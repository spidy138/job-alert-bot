import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from urllib.parse import quote_plus
import os
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def parse_posting_time(time_str: Optional[str]) -> Optional[datetime]:
    """
    Parse posting time string and return datetime object.

    Handles: "1 hour ago", "2 hours ago", "30 minutes ago", "just now", etc.
    """
    if not time_str:
        return None

    time_str = time_str.lower().strip()

    if any(x in time_str for x in ["just now", "moment", "few seconds", "posted today"]):
        return datetime.now()

    import re
    match = re.search(r'(\d+)\s*(hour|minute|day|week|month|h|m|d|w|s)', time_str)
    if match:
        num = int(match.group(1))
        unit = match.group(2)[0].lower()

        if unit in ['m', 'minute']:
            return datetime.now() - timedelta(minutes=num)
        elif unit in ['h', 'hour']:
            return datetime.now() - timedelta(hours=num)
        elif unit in ['d', 'day']:
            return datetime.now() - timedelta(days=num)
        elif unit in ['w', 'week']:
            return datetime.now() - timedelta(weeks=num)

    return None


def is_posted_within_hours(posting_time: Optional[datetime], hours: int) -> bool:
    """Check if job was posted within last N hours"""
    if posting_time is None:
        return False

    time_diff = datetime.now() - posting_time
    return time_diff <= timedelta(hours=hours)


def is_english(text: str) -> bool:
    """Check if text is primarily English"""
    if not text:
        return True
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return (ascii_count / len(text)) > 0.6 if text else True


def is_relevant_location(location_str: str, search_location: str) -> bool:
    """Check if location matches search location"""
    return search_location.lower() in location_str.lower()

class LinkedInSearcher:
    """Search LinkedIn for jobs matching keywords"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def search(self, keywords: List[str], locations: List[str], hours: int) -> List[Dict]:
        """
        Search LinkedIn for jobs with keywords in location within time window.
        
        Args:
            keywords: List of keywords to search
            locations: List of locations to search
            hours: Only return jobs posted within last N hours
        
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        for keyword in keywords:
            for location in locations:
                try:
                    self.logger.log(5, f"Searching LinkedIn: {keyword} in {location}")
                    
                    # Search LinkedIn
                    jobs_found = self._search_keyword_location(keyword, location, hours)
                    jobs.extend(jobs_found)
                    
                    time.sleep(1)  # Rate limiting
                
                except Exception as e:
                    self.logger.warning(f"Error searching LinkedIn {keyword} in {location}: {e}")
        
        return jobs
    
    def _search_keyword_location(self, keyword: str, location: str, hours: int) -> List[Dict]:
        """Search single keyword+location combination on LinkedIn

        LinkedIn time filter (f_TPR): r40000=24h, r604800=7days, r2592000=30days
        Filters jobs by posting date to match the hours parameter.
        """
        jobs = []
        stats = {"total_cards": 0, "parsed": 0, "english": 0, "location": 0, "time": 0, "accepted": 0}

        query = quote_plus(keyword)
        loc = quote_plus(location)

        # Calculate LinkedIn time filter based on hours
        # LinkedIn only supports: 24h (r40000), 7d (r604800), 30d (r2592000)
        # Always use the tightest filter that includes our time window
        if hours <= 24:
            time_filter = "r40000"  # last 24 hours (covers 1-24h requests)
        elif hours <= 168:
            time_filter = "r604800"  # last 7 days (covers 1-168h requests)
        else:
            time_filter = "r2592000"  # last 30 days (covers 1-720h requests)

        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={query}&location={loc}&distance=100&sortBy=DD&f_TPR={time_filter}"
        )

        self.logger.debug(f"LinkedIn: GET {url} (time_filter={time_filter}, hours_requested={hours})")

        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                self.logger.warning(f"LinkedIn HTTP {resp.status_code} for '{keyword}' in {location}")
                return []

            self.logger.debug(f"LinkedIn: Response status {resp.status_code}, content length: {len(resp.text)} bytes")

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li")
            stats["total_cards"] = len(cards)

            self.logger.info(f"LinkedIn: Found {stats['total_cards']} cards for '{keyword}' in {location}")

            for card in cards[:20]:
                try:
                    title_el = card.find("h3", class_="base-search-card__title")
                    company_el = card.find("h4", class_="base-search-card__subtitle")
                    link_el = card.find("a", class_="base-card__full-link")
                    location_el = card.find("span", class_="job-search-card__location")
                    time_el = card.find("span", class_="job-search-card__listdate")
                    desc_el = card.find("p", class_="base-search-card__snippet")

                    if not all([title_el, company_el, link_el]):
                        self.logger.log(5, f"LinkedIn: Skipped incomplete card (missing fields)")
                        continue

                    stats["parsed"] += 1
                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True)
                    link = link_el.get("href", "").split("?")[0]
                    location_text = location_el.get_text(strip=True) if location_el else "Unknown"
                    description = desc_el.get_text(strip=True) if desc_el else "No description"
                    posted_str = time_el.get_text(strip=True) if time_el else ""

                    # Validate: English text
                    if not is_english(title) or not is_english(description):
                        self.logger.log(5, f"LinkedIn: Filtered non-English - '{title[:40]}'")
                        continue
                    stats["english"] += 1

                    # Validate: Location
                    if not is_relevant_location(location_text, location):
                        self.logger.log(5, f"LinkedIn: Filtered location - posted '{location_text}', searching '{location}'")
                        continue
                    stats["location"] += 1

                    # Validate: Posted within time window (post-processing filter)
                    # NOTE: LinkedIn's guest API no longer returns posting time data
                    # If posting time is missing, we accept the job (assume recent)
                    posting_time = parse_posting_time(posted_str)
                    if posted_str and posting_time and not is_posted_within_hours(posting_time, hours):
                        self.logger.log(5, f"LinkedIn: Filtered old - posted '{posted_str}' (threshold: {hours}h)")
                        continue

                    if not posted_str:
                        self.logger.log(5, f"LinkedIn: No posting time in HTML (LinkedIn API limitation) - accepting job")

                    stats["time"] += 1

                    jobs.append({
                        "title": title,
                        "company": company,
                        "link": link,
                        "location": location_text,
                        "description": description,
                        "posted": posted_str if posted_str else "Recently",
                        "posted_datetime": posting_time,
                        "source": "LinkedIn",
                        "skill": keyword,
                        "portal": "linkedin",
                    })

                    stats["accepted"] += 1
                    self.logger.log(5, f"LinkedIn: Accepted - '{title[:60]}' @ {company}")

                except Exception as e:
                    self.logger.log(5, f"LinkedIn: Error parsing card - {e}")
                    continue

            # Log summary statistics
            self.logger.info(
                f"LinkedIn summary: {stats['total_cards']} cards -> "
                f"{stats['parsed']} parsed -> "
                f"{stats['english']} English -> "
                f"{stats['location']} location match -> "
                f"{stats['accepted']} accepted (time filter: SKIPPED - no API data)"
            )

        except Exception as e:
            self.logger.error(f"LinkedIn search error for '{keyword}' in {location}: {e}")

        return jobs


class NaukriSearcher:
    """Search Naukri for jobs matching keywords"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.nkparam = self._load_nkparam()

    def _load_nkparam(self) -> str:
        """Load nkparam from saved session file, extract fresh if needed"""
        session_file = "naukri_session.json"

        # Try to load from file
        if os.path.exists(session_file):
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                    nkparam = data.get("nkparam")
                    if nkparam:
                        self.logger.log(5, f"Naukri: Loaded nkparam from {session_file}")
                        return nkparam
            except Exception as e:
                self.logger.log(5, f"Naukri: Could not load session file: {e}")

        # Fallback to hardcoded value (will need manual refresh if expired)
        self.logger.log(5, f"Naukri: No session file found, using default nkparam")
        return "KGxYt2w1E12Y6PmzZdi1CfkHhfrlIuSg4Mztslb8ezmDVUstPnDaLx1e2zNQaZM04ZhXkUDLnoPw65kO4XYZGQ=="
    
    def search(self, keywords: List[str], locations: List[str], hours: int) -> List[Dict]:
        """
        Search Naukri for jobs with keywords in location within time window.
        
        Args:
            keywords: List of keywords to search
            locations: List of locations to search (Naukri India only)
            hours: Only return jobs posted within last N hours
        
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        for keyword in keywords:
            for location in locations:
                try:
                    self.logger.log(5, f"Searching Naukri: {keyword} in {location}")
                    
                    # Search Naukri
                    jobs_found = self._search_keyword_location(keyword, location, hours)
                    jobs.extend(jobs_found)
                    
                    time.sleep(1)  # Rate limiting
                
                except Exception as e:
                    self.logger.warning(f"Error searching Naukri {keyword} in {location}: {e}")
        
        return jobs
    
    def _search_keyword_location(self, keyword: str, location: str, hours: int) -> List[Dict]:
        """Search single keyword+location combination on Naukri using jobapi/v3/search

        IMPORTANT: Naukri provides jobs via jobapi/v3/search endpoint (JSON API).
        API requires nkparam authentication token. Naukri only provides jobs from last 24 hours.
        Time filtering is converted from hours to days (minimum 1 day).
        """
        jobs = []
        stats = {"total_found": 0, "parsed": 0, "english": 0, "location": 0, "time": 0, "accepted": 0}

        # Naukri India only
        if location.lower() not in ["bangalore", "bengaluru"]:
            self.logger.info(f"Naukri: Skipping '{location}' (India only)")
            return []

        # Convert hours to days for jobAge parameter (minimum 1 day)
        job_age_days = max(1, hours // 24)

        url = "https://www.naukri.com/jobapi/v3/search"
        params = {
            "noOfResults": 20,
            "urlType": "search_by_key_loc",
            "searchType": "adv",
            "location": "bengaluru" if location.lower() in ["bangalore", "bengaluru"] else location.lower(),
            "keyword": keyword,
            "sort": "recency",
            "pageNo": 1,
            "jobAge": job_age_days,
            "seoKey": f"{keyword.replace(' ', '-')}-jobs-in-{location.lower()}",
            "src": "directSearch",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "appid": "109",
            "clientid": "d3skt0p",
            "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
            "systemid": "Naukri",
            "nkparam": self.nkparam,
            "Referer": f"https://www.naukri.com/{keyword.replace(' ', '-')}-jobs-in-{location.lower()}?sort=recency&jobAge={job_age_days}",
        }

        self.logger.debug(f"Naukri: GET {url} (keyword={keyword}, location={location}, jobAge={job_age_days}d)")

        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=15)

            if resp.status_code != 200:
                self.logger.warning(f"Naukri HTTP {resp.status_code} for '{keyword}' in {location}")
                return []

            self.logger.debug(f"Naukri: Response status {resp.status_code}, content length: {len(resp.text)} bytes")

            data = resp.json()
            job_details = data.get("jobDetails", [])
            stats["total_found"] = len(job_details)

            self.logger.info(f"Naukri: Found {stats['total_found']} jobs for '{keyword}' in {location} (jobAge={job_age_days}d)")

            for job_data in job_details[:20]:
                try:
                    title = job_data.get("title", "")
                    company = job_data.get("companyName", "Unknown")
                    link = job_data.get("jdURL", "")
                    # Naukri API doesn't provide location, extract from title or other fields
                    location_text = job_data.get("location", "")
                    if not location_text:
                        # Try to extract from other fields or use title
                        location_text = job_data.get("jobLocation", "")
                        if not location_text:
                            # Location might be in the title
                            location_text = "Bengaluru"  # Assume search location if not found
                    description = job_data.get("jobDescription", title)

                    if not title:
                        self.logger.log(5, f"Naukri: Skipped job with no title")
                        continue

                    stats["parsed"] += 1

                    # Convert timestamp to string (createdDate is in milliseconds)
                    created_ms = job_data.get("createdDate", 0)
                    if created_ms:
                        posting_time = datetime.fromtimestamp(created_ms / 1000.0)
                        posted_str = posting_time.strftime("%d %b")
                    else:
                        posting_time = None
                        posted_str = "Recently"

                    # Validate: English text
                    if not is_english(title) or not is_english(description):
                        self.logger.log(5, f"Naukri: Filtered non-English - '{title[:40]}'")
                        continue
                    stats["english"] += 1

                    # Validate: Location
                    if not is_relevant_location(location_text, location):
                        self.logger.log(5, f"Naukri: Filtered location - job in '{location_text}', searching '{location}'")
                        continue
                    stats["location"] += 1

                    # Validate: Posted within time window
                    days_threshold = max(1, hours // 24)
                    if posting_time:
                        hours_ago = (datetime.now() - posting_time).total_seconds() / 3600
                        if hours_ago > (days_threshold * 24):
                            self.logger.log(5, f"Naukri: Filtered old - posted {days_ago:.0f} days ago (threshold: {days_threshold}d)")
                            continue
                    else:
                        self.logger.log(5, f"Naukri: No posting time found - accepting job")

                    stats["time"] += 1

                    jobs.append({
                        "title": title,
                        "company": company,
                        "link": link,
                        "location": location_text,
                        "description": description,
                        "posted": posted_str,
                        "posted_datetime": posting_time,
                        "source": "Naukri",
                        "skill": keyword,
                        "portal": "naukri",
                    })

                    stats["accepted"] += 1
                    self.logger.log(5, f"Naukri: Accepted - '{title[:60]}' @ {company}")

                except Exception as e:
                    self.logger.log(5, f"Naukri: Error parsing job - {e}")
                    continue

            # Log summary statistics
            days_threshold = max(1, hours // 24)
            self.logger.info(
                f"Naukri summary: {stats['total_found']} found -> "
                f"{stats['parsed']} parsed -> "
                f"{stats['english']} English -> "
                f"{stats['location']} location match -> "
                f"{stats['time']} recent (threshold: {days_threshold}d) -> "
                f"{stats['accepted']} accepted"
            )

        except Exception as e:
            self.logger.error(f"Naukri search error for '{keyword}' in {location}: {e}")

        return jobs
