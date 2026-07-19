"""
Discord Channel Purge - Actually deletes old messages.

A webhook CANNOT delete messages. This uses a Discord BOT TOKEN instead.

Setup required:
  1. Create a bot at https://discord.com/developers/applications
  2. Give it "Manage Messages" + "Read Message History" permissions
  3. Invite the bot to your server
  4. Enable "Message Content Intent" (not strictly needed for delete)
  5. Get your CHANNEL ID (right-click channel > Copy Channel ID, needs Developer Mode on)

Environment Variables:
  DISCORD_BOT_TOKEN   - Your bot token
  DISCORD_CHANNEL_ID  - The channel to purge
  PURGE_OLDER_THAN_H  - (optional) only delete messages older than N hours, default 0 = all
"""

import os
import time
import requests
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
PURGE_OLDER_THAN_H = int(os.getenv("PURGE_OLDER_THAN_H", "0"))

if not BOT_TOKEN or not CHANNEL_ID:
    print("❌ DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID must both be set")
    exit(1)

API = "https://discord.com/api/v10"
HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json",
}


def get_messages(before=None, limit=100):
    """Fetch up to `limit` messages from the channel."""
    url = f"{API}/channels/{CHANNEL_ID}/messages?limit={limit}"
    if before:
        url += f"&before={before}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        print(f"❌ Failed to fetch messages: {resp.status_code} {resp.text[:200]}")
        return []
    return resp.json()


def bulk_delete(message_ids):
    """Bulk delete messages (2-100 at a time, must be < 14 days old)."""
    url = f"{API}/channels/{CHANNEL_ID}/messages/bulk-delete"
    resp = requests.post(url, headers=HEADERS, json={"messages": message_ids}, timeout=15)
    return resp.status_code == 204, resp


def delete_single(message_id):
    """Delete one message (used for messages > 14 days old)."""
    url = f"{API}/channels/{CHANNEL_ID}/messages/{message_id}"
    resp = requests.delete(url, headers=HEADERS, timeout=15)
    return resp.status_code == 204


def should_delete(msg) -> bool:
    """Respect the PURGE_OLDER_THAN_H window if set."""
    if PURGE_OLDER_THAN_H <= 0:
        return True
    ts = msg.get("timestamp", "")
    try:
        msg_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=PURGE_OLDER_THAN_H)
    return msg_time < cutoff


def main():
    print(f"🧹 Purging channel {CHANNEL_ID}")
    if PURGE_OLDER_THAN_H > 0:
        print(f"   Only deleting messages older than {PURGE_OLDER_THAN_H}h")
    else:
        print(f"   Deleting ALL messages")

    total_deleted = 0
    before = None
    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)

    while True:
        messages = get_messages(before=before)
        if not messages:
            break

        before = messages[-1]["id"]  # paginate

        # Split into recent (bulk-deletable) and old (single-delete)
        recent_ids = []
        old_ids = []
        for msg in messages:
            if not should_delete(msg):
                continue
            try:
                msg_time = datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
            except Exception:
                msg_time = datetime.now(timezone.utc)

            if msg_time > fourteen_days_ago:
                recent_ids.append(msg["id"])
            else:
                old_ids.append(msg["id"])

        # Bulk delete recent messages
        if len(recent_ids) >= 2:
            ok, resp = bulk_delete(recent_ids)
            if ok:
                total_deleted += len(recent_ids)
                print(f"   ✅ Bulk deleted {len(recent_ids)}")
            elif resp.status_code == 429:  # rate limited
                retry = resp.json().get("retry_after", 2)
                print(f"   ⏳ Rate limited, waiting {retry}s")
                time.sleep(retry + 0.5)
                continue
            else:
                print(f"   ⚠️ Bulk delete failed: {resp.status_code} {resp.text[:150]}")
        elif len(recent_ids) == 1:
            if delete_single(recent_ids[0]):
                total_deleted += 1

        # Single-delete old messages (Discord won't bulk-delete >14 days)
        for mid in old_ids:
            if delete_single(mid):
                total_deleted += 1
                time.sleep(0.4)  # avoid rate limit

        time.sleep(1)  # pacing between pages

    print(f"\n✅ Purge complete. Deleted {total_deleted} message(s).")


if __name__ == "__main__":
    main()
