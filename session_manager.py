#!/usr/bin/env python3
"""Extract and manage Naukri session parameters (nkparam, cookies)"""

import requests
import re
import json
from datetime import datetime

class NaukriSessionManager:
    """Manages Naukri API session credentials"""

    def __init__(self):
        self.session = requests.Session()
        self.nkparam = None
        self.cookies = None
        self.last_updated = None

    def extract_session(self, keyword="node", location="bengaluru"):
        """Extract fresh nkparam and cookies from Naukri"""

        url = f"https://www.naukri.com/{keyword.replace(' ', '-')}-jobs-in-{location}?sort=recency&jobAge=1"

        print(f"[1] Fetching Naukri page: {url}")
        try:
            # Set browser-like user agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            }

            resp = self.session.get(url, headers=headers, timeout=15)
            print(f"    Status: {resp.status_code}\n")

            # Extract nkparam from HTML
            print("[2] Searching for nkparam in response...")
            nkparam = self._extract_nkparam_from_html(resp.text)

            if nkparam:
                print(f"    ✓ Found: {nkparam[:50]}...\n")
                self.nkparam = nkparam
            else:
                print("    ✗ Not found in HTML\n")

            # Get cookies
            print("[3] Extracting cookies...")
            self.cookies = self.session.cookies.get_dict()
            print(f"    ✓ Found {len(self.cookies)} cookies\n")

            self.last_updated = datetime.now()

            # Validate by making a test API call
            print("[4] Validating with API call...")
            if self._validate_session(keyword, location):
                print("    ✓ Session valid!\n")
                return True
            else:
                print("    ✗ Session validation failed\n")
                return False

        except Exception as e:
            print(f"    ✗ Error: {e}\n")
            return False

    def _extract_nkparam_from_html(self, html):
        """Try multiple patterns to extract nkparam from HTML"""

        patterns = [
            r'"nkparam"\s*:\s*"([^"]+)"',
            r'nkparam["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'"nkparam":"([^"]+)"',
            r"nkparam\s*=\s*['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

        return None

    def _validate_session(self, keyword="node", location="bengaluru"):
        """Test if session is valid by making an API call"""

        try:
            params = {
                "noOfResults": 20,
                "urlType": "search_by_key_loc",
                "searchType": "adv",
                "location": location,
                "keyword": keyword,
                "sort": "recency",
                "pageNo": 1,
                "jobAge": 1,
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "appid": "109",
                "clientid": "d3skt0p",
                "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
                "systemid": "Naukri",
            }

            if self.nkparam:
                headers["nkparam"] = self.nkparam

            resp = self.session.get(
                "https://www.naukri.com/jobapi/v3/search",
                params=params,
                headers=headers,
                timeout=10
            )

            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("jobDetails", [])
                return len(jobs) > 0, data if len(jobs) > 0 else None
            else:
                print(f"       API returned {resp.status_code}")
                return False, None

        except Exception as e:
            print(f"       Error: {e}")
            return False, None

    def fetch_jobs(self, keyword="node", location="bengaluru"):
        """Fetch and display jobs using current session"""

        try:
            params = {
                "noOfResults": 20,
                "urlType": "search_by_key_loc",
                "searchType": "adv",
                "location": location,
                "keyword": keyword,
                "sort": "recency",
                "pageNo": 1,
                "jobAge": 1,
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "appid": "109",
                "clientid": "d3skt0p",
                "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
                "systemid": "Naukri",
            }

            if self.nkparam:
                headers["nkparam"] = self.nkparam

            print(f"\n[Fetching jobs] keyword={keyword}, location={location}\n")

            resp = self.session.get(
                "https://www.naukri.com/jobapi/v3/search",
                params=params,
                headers=headers,
                timeout=10
            )

            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("jobDetails", [])

                print(f"✓ Found {len(jobs)} jobs:\n")
                print("-" * 100)

                for i, job in enumerate(jobs[:10], 1):
                    title = job.get("title", "N/A")[:70]
                    company = job.get("companyName", "N/A")[:40]
                    created = job.get("createdDate", 0)

                    if created:
                        posted_date = datetime.fromtimestamp(created / 1000.0).strftime("%d %b %Y %H:%M")
                    else:
                        posted_date = "N/A"

                    print(f"{i:2}. {title:<70} | {company:<40} | {posted_date}")

                print("-" * 100)
                print(f"\nTotal: {len(jobs)} jobs\n")

                return True
            else:
                print(f"✗ API Error: {resp.status_code}")
                if resp.status_code == 406:
                    print("  → Token expired, get fresh nkparam from browser\n")
                return False

        except Exception as e:
            print(f"✗ Error: {e}\n")
            return False

    def get_headers(self):
        """Get API headers with current session credentials"""

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "appid": "109",
            "clientid": "d3skt0p",
            "gid": "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
            "systemid": "Naukri",
        }

        if self.nkparam:
            headers["nkparam"] = self.nkparam

        return headers

    def save_to_file(self, filepath="naukri_session.json"):
        """Save session credentials to file"""

        data = {
            "nkparam": self.nkparam,
            "cookies": self.cookies,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"[✓] Session saved to {filepath}\n")

    def load_from_file(self, filepath="naukri_session.json"):
        """Load session credentials from file"""

        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            self.nkparam = data.get("nkparam")
            self.cookies = data.get("cookies", {})
            last_updated = data.get("last_updated")

            if last_updated:
                self.last_updated = datetime.fromisoformat(last_updated)

            print(f"[✓] Session loaded from {filepath}")
            if self.last_updated:
                print(f"    Last updated: {self.last_updated.strftime('%Y-%m-%d %H:%M:%S')}\n")

            return True
        except FileNotFoundError:
            return False

if __name__ == "__main__":
    import sys

    manager = NaukriSessionManager()

    print("=" * 80)
    print("Naukri Session Manager")
    print("=" * 80 + "\n")

    # Check if nkparam provided as argument
    if len(sys.argv) > 1:
        nkparam = sys.argv[1]
        print(f"[1] Using provided nkparam: {nkparam[:50]}...\n")
        manager.nkparam = nkparam

        print("[2] Validating with API call...")
        valid, data = manager._validate_session("node", "bengaluru")

        if valid:
            print("[✓] Token valid!\n")

            print("[3] Fetching jobs...")
            if manager.fetch_jobs("node", "bengaluru"):
                manager.save_to_file()
                print("[✓] SUCCESS! Credentials saved to naukri_session.json\n")
            else:
                print("[✗] Could not fetch jobs.\n")
        else:
            print("[✗] Validation failed. Token might be invalid.\n")
    else:
        print("USAGE:")
        print("  python session_manager.py <nkparam>\n")
        print("HOW TO GET nkparam:")
        print("  1. Open: https://www.naukri.com/node-jobs-in-bengaluru?sort=recency&jobAge=1")
        print("  2. Press F12 → Network tab")
        print("  3. Search for request: 'jobapi/v3/search'")
        print("  4. Look for header 'nkparam' in Request Headers")
        print("  5. Copy the value")
        print("  6. Run: python session_manager.py <paste-nkparam-here>\n")
        print("EXAMPLE:")
        print("  python session_manager.py KGxYt2w1E12Y6PmzZdi1CfkHhfrlIuSg4Mztslb8ezmDVUstPnDaLx1e2zNQaZM04ZhXkUDLnoPw65kO4XYZGQ==\n")
