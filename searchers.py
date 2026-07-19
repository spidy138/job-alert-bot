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
        """Search single keyword+location combination"""
        # Placeholder - will be filled in Task 5
        return []


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
        """Search single keyword+location combination"""
        # Placeholder - will be filled in Task 6
        return []
