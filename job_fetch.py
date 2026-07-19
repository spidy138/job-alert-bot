#!/usr/bin/env python3
"""
Job Alert Bot v4 - Main Orchestration Script

Features:
- CLI argument parsing with --profile and --location
- Config-driven search parameters
- Resume-based keyword extraction
- Multi-portal job search (LinkedIn, Naukri)
- Discord notifications
- Persistent seen jobs tracking

Usage:
    python job_fetch.py --profile dataeng --location Bangalore
    python job_fetch.py --profile frontend --location Berlin --config custom-config.json
"""

import argparse
import json
import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Set, List
from datetime import datetime

from config import load_config, validate_config, resolve_search_keywords
from logger import setup_logger
from searchers import LinkedInSearcher, NaukriSearcher
from discord_client import DiscordClient

SEEN_JOBS_FILE = Path(__file__).parent / "seen_jobs.json"
RESUME_FILE = Path(__file__).parent / "resume.txt"


def load_resume() -> str:
    """
    Load and return resume text (lowercased).

    Returns:
        Lowercased resume text if file exists, empty string otherwise
    """
    if RESUME_FILE.exists():
        return RESUME_FILE.read_text().lower()
    return ""


def load_seen_jobs() -> Dict[str, Set[str]]:
    """
    Load seen jobs tracking from JSON file.

    The seen_jobs.json file tracks job postings per profile:location combination
    to prevent duplicate notifications. Format:

        {
          "profile-name:location": ["hash1", "hash2", ...],
          "another-profile:location": ["hash3", ...]
        }

    Each hash is MD5(title + company + link) and uniquely identifies a job posting.

    Returns:
        Dictionary mapping profile:location keys to sets of seen job hashes.
        Returns empty dict if file doesn't exist or is malformed.

    Note:
        - Auto-creates file on first save if missing
        - Converts JSON lists to Python sets for O(1) lookup performance
        - Keeps last 10,000 hashes per profile:location to prevent unbounded growth
    """
    if SEEN_JOBS_FILE.exists():
        try:
            data = json.loads(SEEN_JOBS_FILE.read_text())
            # Convert lists back to sets for O(1) lookups
            return {k: set(v) for k, v in data.items()}
        except Exception:
            return {}
    return {}


def save_seen_jobs(seen: Dict[str, Set[str]]):
    """
    Save seen jobs tracking to JSON file.

    Persists the job tracking state to enable duplicate prevention across runs.
    Each profile:location combination maintains its own independent history.

    Args:
        seen: Dictionary mapping profile:location keys to sets of job hashes.
              Format: {"profile-name:location": {"hash1", "hash2", ...}, ...}

    Implementation details:
        - Converts Python sets to JSON lists for serialization
        - Keeps only last 10,000 hashes per profile:location to prevent file bloat
        - Creates file at SEEN_JOBS_FILE if it doesn't exist
        - Prettifies output with 2-space indentation for readability

    Hash calculation: MD5(title|company|link) as hex string
    """
    # Convert sets to lists for JSON serialization
    # Keep last 10k per profile to avoid unbounded growth
    data = {k: list(v)[-10000:] for k, v in seen.items()}
    SEEN_JOBS_FILE.write_text(json.dumps(data, indent=2))


def job_id(title: str, company: str, link: str) -> str:
    """
    Generate unique ID for job using MD5 hash.

    Args:
        title: Job title
        company: Company name
        link: Job posting link

    Returns:
        32-character hex MD5 hash
    """
    raw = f"{title}|{company}|{link}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_searcher(portal: str, logger: logging.Logger):
    """
    Get appropriate searcher instance for the given portal.

    Args:
        portal: Portal name ("linkedin" or "naukri")
        logger: Logger instance

    Returns:
        Searcher instance (LinkedInSearcher or NaukriSearcher)

    Raises:
        ValueError: If portal is unknown
    """
    if portal.lower() == "linkedin":
        return LinkedInSearcher(logger)
    elif portal.lower() == "naukri":
        return NaukriSearcher(logger)
    else:
        raise ValueError(f"Unknown portal: {portal}")


def main():
    """
    Main orchestration function.

    Loads config, validates profile, searches job portals, filters seen jobs,
    sends Discord notifications, and saves state.
    """
    # ─── CLI ARGUMENT PARSING ─────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Job Alert Bot v4 - Search jobs and send Discord notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python job_fetch.py --profile dataeng --location Bangalore
  python job_fetch.py --profile frontend --location Berlin --config custom.json
        """
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Profile name from config (e.g., 'dataeng', 'frontend')"
    )
    parser.add_argument(
        "--location",
        required=True,
        help="Location to search (e.g., 'Bangalore', 'Berlin')"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file (default: config.json)"
    )

    args = parser.parse_args()

    # ─── LOAD AND VALIDATE CONFIG ─────────────────────────────────────────────
    try:
        config = load_config(args.config)
        validate_config(config)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        exit(1)
    except ValueError as e:
        print(f"ERROR: Config validation failed: {e}")
        exit(1)

    # ─── SETUP LOGGING ────────────────────────────────────────────────────────
    log_level = config.get("logging", {}).get("level", "INFO")
    logger = setup_logger(log_level)

    logger.info(f"Starting Job Alert Bot - Profile: {args.profile}, Location: {args.location}")

    # ─── VALIDATE PROFILE ─────────────────────────────────────────────────────
    if args.profile not in config["profiles"]:
        logger.error(f"Profile '{args.profile}' not found in config")
        exit(1)

    profile = config["profiles"][args.profile]

    # ─── LOAD RESUME ──────────────────────────────────────────────────────────
    resume_text = load_resume()
    if not resume_text:
        logger.warning("resume.txt not found, using profile keywords only")
    else:
        logger.info("Resume loaded successfully")

    # ─── RESOLVE KEYWORDS ─────────────────────────────────────────────────────
    try:
        keywords = resolve_search_keywords(config, args.profile, resume_text)
        if not keywords:
            logger.error("No keywords found to search")
            exit(1)

        keywords_list = sorted(keywords)
        display_keywords = keywords_list[:10]
        display_str = ", ".join(display_keywords)
        if len(keywords_list) > 10:
            display_str += f"... ({len(keywords_list)} total)"

        logger.info(f"Keywords resolved: {display_str}")

    except ValueError as e:
        logger.error(f"Error resolving keywords: {e}")
        exit(1)

    # ─── GET SEARCH PARAMETERS ────────────────────────────────────────────────
    locations = [args.location]
    hours = profile.get("hours", 24)
    portal = profile.get("portal", "all")

    logger.info(f"Search parameters: {hours} hours, {len(keywords)} keywords, location: {args.location}")

    # ─── LOAD SEEN JOBS ───────────────────────────────────────────────────────
    seen = load_seen_jobs()
    profile_location_key = f"{args.profile}:{args.location}"
    if profile_location_key not in seen:
        seen[profile_location_key] = set()

    logger.log(5, f"Loaded {len(seen[profile_location_key])} previously seen jobs for this profile:location")

    # ─── SEARCH PORTALS ───────────────────────────────────────────────────────
    all_jobs: List[Dict] = []

    linkedin_enabled = config.get("linkedin", {}).get("enabled", True)
    naukri_enabled = config.get("naukri", {}).get("enabled", True)

    if (portal in ["all", "linkedin"]) and linkedin_enabled:
        logger.info("Searching LinkedIn...")
        try:
            linkedin_searcher = LinkedInSearcher(logger)
            linkedin_jobs = linkedin_searcher.search(list(keywords), locations, hours)
            all_jobs.extend(linkedin_jobs)
            logger.info(f"LinkedIn: found {len(linkedin_jobs)} jobs")
        except Exception as e:
            logger.error(f"LinkedIn search error: {e}")
    elif portal in ["all", "linkedin"] and not linkedin_enabled:
        logger.info("LinkedIn: disabled in config")

    if (portal in ["all", "naukri"]) and naukri_enabled:
        logger.info("Searching Naukri...")
        try:
            naukri_searcher = NaukriSearcher(logger)
            naukri_jobs = naukri_searcher.search(list(keywords), locations, hours)
            all_jobs.extend(naukri_jobs)
            logger.info(f"Naukri: found {len(naukri_jobs)} jobs")
        except Exception as e:
            logger.error(f"Naukri search error: {e}")
    elif portal in ["all", "naukri"] and not naukri_enabled:
        logger.info("Naukri: disabled in config")

    # ─── FILTER OUT SEEN JOBS ─────────────────────────────────────────────────
    new_jobs = []
    for job in all_jobs:
        jid = job_id(job["title"], job["company"], job["link"])
        if jid not in seen[profile_location_key]:
            seen[profile_location_key].add(jid)
            new_jobs.append(job)

    logger.info(f"New jobs found: {len(new_jobs)} (out of {len(all_jobs)} total)")

    # ─── SEND TO DISCORD ──────────────────────────────────────────────────────
    if new_jobs:
        try:
            webhook_url_env = config["discord"]["webhook_url_env"]
            webhook_url = os.getenv(webhook_url_env)

            if not webhook_url:
                logger.error(f"Environment variable '{webhook_url_env}' not set")
                exit(1)

            discord = DiscordClient(webhook_url, logger)
            discord.send_jobs(new_jobs, args.profile)

        except Exception as e:
            logger.error(f"Discord notification error: {e}")
            exit(1)
    else:
        logger.info("No new jobs to notify")

    # ─── SAVE STATE ────────────────────────────────────────────────────────────
    save_seen_jobs(seen)
    logger.info(f"State saved - Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
