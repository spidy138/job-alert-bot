import requests
import logging
from typing import List, Dict, Optional

def format_job_embed(job: Dict) -> Optional[Dict]:
    """Format single job as Discord embed with validation"""
    try:
        # Validate and sanitize required fields
        title = str(job.get("title", "No Title"))[:200]
        company = str(job.get("company", "Unknown"))[:100]
        location = str(job.get("location", "Unknown"))[:100]
        skill = str(job.get("skill", "general")).title()[:50]
        posted = str(job.get("posted", "Recently"))[:50]
        link = str(job.get("link", ""))[:2000]
        description = str(job.get("description", title))
        source = str(job.get("source", "Portal"))[:50]

        # Truncate description
        if len(description) > 300:
            description = description[:300] + "..."

        # Only add link if valid
        desc_line = f"**{description}**\n\n**Posted:** {posted}"
        if link and link.startswith("http"):
            desc_line += f"\n\n[Apply]({link})"

        embed = {
            "title": title,
            "description": desc_line,
            "fields": [
                {"name": "Company", "value": company or "Unknown", "inline": True},
                {"name": "Location", "value": location or "Unknown", "inline": True},
                {"name": "Skill", "value": skill or "General", "inline": True},
            ],
            "color": 5763719,
            "footer": {"text": f"via {source}"},
        }
        return embed
    except Exception as e:
        return None

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
            embed = format_job_embed(job)
            if embed:
                embeds.append(embed)
            else:
                self.logger.log(5, f"Skipped job with invalid data: {job.get('title', 'Unknown')}")

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
                error_msg = f"Discord webhook returned {resp.status_code}"
                try:
                    error_detail = resp.json()
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {resp.text[:200]}"

                self.logger.error(error_msg)
                return False

        except Exception as e:
            self.logger.error(f"Discord webhook error: {e}")
            return False
