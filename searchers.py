import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from urllib.parse import quote_plus

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
        """Search single keyword+location combination on LinkedIn"""
        jobs = []

        query = quote_plus(keyword)
        loc = quote_plus(location)

        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={query}&location={loc}&distance=100&sortBy=DD"
        )

        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                self.logger.debug(f"LinkedIn HTTP {resp.status_code} for {keyword}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li")

            for card in cards[:20]:
                try:
                    title_el = card.find("h3", class_="base-search-card__title")
                    company_el = card.find("h4", class_="base-search-card__subtitle")
                    link_el = card.find("a", class_="base-card__full-link")
                    location_el = card.find("span", class_="job-search-card__location")
                    time_el = card.find("span", class_="job-search-card__listdate")
                    desc_el = card.find("p", class_="base-search-card__snippet")

                    if not all([title_el, company_el, link_el]):
                        continue

                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True)
                    link = link_el.get("href", "").split("?")[0]
                    location_text = location_el.get_text(strip=True) if location_el else "Unknown"
                    description = desc_el.get_text(strip=True) if desc_el else "No description"
                    posted_str = time_el.get_text(strip=True) if time_el else ""

                    # Validate
                    if not is_english(title) or not is_english(description):
                        self.logger.log(5, f"LinkedIn: Filtered non-English - {title[:30]}")
                        continue

                    if not is_relevant_location(location_text, location):
                        self.logger.log(5, f"LinkedIn: Filtered wrong location - {location_text}")
                        continue

                    posting_time = parse_posting_time(posted_str)
                    if not is_posted_within_hours(posting_time, hours):
                        self.logger.log(5, f"LinkedIn: Filtered old posting - {posted_str}")
                        continue

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

                    self.logger.log(5, f"LinkedIn: Found job - {title[:50]}")

                except Exception as e:
                    self.logger.log(5, f"LinkedIn: Error parsing job card - {e}")
                    continue

        except Exception as e:
            self.logger.warning(f"LinkedIn search error: {e}")

        return jobs


class NaukriSearcher:
    """Search Naukri for jobs matching keywords"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
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
        """Search single keyword+location combination on Naukri"""
        jobs = []

        # Naukri India only
        if location.lower() not in ["bangalore", "bengaluru"]:
            self.logger.log(5, f"Naukri: Skipping {location} (India only)")
            return []

        skill_slug = keyword.replace(" ", "-").lower()
        location_slug = "bengaluru" if location.lower() in ["bangalore", "bengaluru"] else location.lower()

        url = f"https://www.naukri.com/{skill_slug}-jobs-in-{location_slug}?experience=4,5,6,7,8"

        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                self.logger.debug(f"Naukri HTTP {resp.status_code} for {keyword}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.find_all("article", class_="jobTuple")

            for article in articles[:20]:
                try:
                    title_el = article.find("a", class_="title")
                    company_el = article.find("a", class_="subTitle")

                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True) if company_el else "Unknown"
                    link = title_el.get("href", "")

                    # Get location
                    loc_els = article.find_all("li", class_="fleft")
                    location_text = loc_els[0].get_text(strip=True) if loc_els else "Unknown"

                    # Get description
                    desc_el = article.find("p", class_="job-desc")
                    description = desc_el.get_text(strip=True) if desc_el else title

                    # Get posting time
                    time_el = article.find("span", class_="fleft grey-text br2 placeHolderLi")
                    posted_str = time_el.get_text(strip=True) if time_el else ""

                    # Validate
                    if not is_english(title) or not is_english(description):
                        self.logger.log(5, f"Naukri: Filtered non-English - {title[:30]}")
                        continue

                    if not is_relevant_location(location_text, location):
                        self.logger.log(5, f"Naukri: Filtered wrong location - {location_text}")
                        continue

                    posting_time = parse_posting_time(posted_str)
                    if not is_posted_within_hours(posting_time, hours):
                        self.logger.log(5, f"Naukri: Filtered old posting - {posted_str}")
                        continue

                    jobs.append({
                        "title": title,
                        "company": company,
                        "link": link,
                        "location": location_text,
                        "description": description,
                        "posted": posted_str if posted_str else "Recently",
                        "posted_datetime": posting_time,
                        "source": "Naukri",
                        "skill": keyword,
                        "portal": "naukri",
                    })

                    self.logger.log(5, f"Naukri: Found job - {title[:50]}")

                except Exception as e:
                    self.logger.log(5, f"Naukri: Error parsing job card - {e}")
                    continue

        except Exception as e:
            self.logger.warning(f"Naukri search error: {e}")

        return jobs
