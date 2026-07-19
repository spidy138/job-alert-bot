import requests
import logging
from typing import List, Dict, Optional

def format_job_embed(job: Dict) -> Dict:
    """Format single job as Discord embed"""
    desc = job["description"]
    if len(desc) > 300:
        desc = desc[:300] + "..."

    embed = {
        "title": job["title"][:200],
        "description": f"**{desc}**\n\n**Posted:** {job['posted']}\n\n[Apply]({job['link']})",
        "fields": [
            {"name": "Company", "value": job["company"], "inline": True},
            {"name": "Location", "value": job["location"], "inline": True},
            {"name": "Skill Matched", "value": job["skill"].title(), "inline": True},
        ],
        "color": 5763719,
        "footer": {"text": f"via {job.get('source', 'Portal')} • Posted {job['posted']}"},
    }
    return embed

class DiscordClient:
    """Send job notifications to Discord"""

    def __init__(self, webhook_url: str, logger: logging.Logger):
        self.webhook_url = webhook_url
        self.logger = logger

    def send_jobs(self, jobs: List[Dict], profile_name: str) -> bool:
        """
        Send jobs to Discord via webhook.

        Args:
            jobs: List of job dictionaries
            profile_name: Name of profile searched

        Returns:
            True if successful or no jobs, False if webhook failed
        """
        if not jobs:
            self.logger.log(5, f"No new jobs for profile '{profile_name}'")
            return True

        embeds = []

        # Header embed
        embeds.append({
            "title": f"🎯 {profile_name.title()} Jobs",
            "description": f"Found {len(jobs)} fresh job(s) in the last search",
            "color": 3447003,
            "footer": {"text": f"Job Alert Bot"},
        })

        # Add job embeds (max 10 per message)
        for job in jobs[:10]:
            embeds.append(format_job_embed(job))

        # Send to Discord
        success = self._send_webhook(embeds)

        if success:
            self.logger.info(f"✅ Sent {len(jobs)} job(s) to Discord for profile '{profile_name}'")
        else:
            self.logger.error(f"❌ Failed to send {len(jobs)} job(s) to Discord")

        return success

    def _send_webhook(self, embeds: List[Dict]) -> bool:
        """Send embeds to Discord webhook"""
        try:
            payload = {"embeds": embeds}
            resp = requests.post(self.webhook_url, json=payload, timeout=10)

            if resp.status_code == 204:
                return True
            else:
                self.logger.error(f"Discord webhook returned {resp.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Discord webhook error: {e}")
            return False
