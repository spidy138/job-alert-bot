# Job Alert Bot v4 - Modular Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor job_fetch.py into modular architecture with profile-based search, independent cron schedules per profile, configurable logging, and parallel workflow execution.

**Architecture:** Five focused modules (config, logger, searchers, discord_client, job_fetch) handle loading config/resume, logging, portal-specific scraping, Discord notifications, and orchestration. Profiles define search keywords and optional filters (seniority, years). GitHub Actions runs one workflow per profile with location parallelization via matrix strategy.

**Tech Stack:** Python 3.11, BeautifulSoup4, Requests, JSON, GitHub Actions

## Global Constraints

- CLI requires `--profile {name}` and `--location {name}` arguments (no defaults)
- Logging levels: INFO (default), DEBUG, VERBOSE
- Config file required at startup (no fallback)
- Seen jobs tracked per profile + location combination
- All optional profile fields (seniority, min_years) gracefully skipped if missing
- Discord webhook URL read from DISCORD_WEBHOOK_URL environment variable

---

## File Structure

```
job_alert_bot/
├── config.py              # Config loading, validation, keyword resolution
├── logger.py              # Centralized logging setup (INFO/DEBUG/VERBOSE)
├── searchers.py           # LinkedInSearcher, NaukriSearcher classes
├── discord_client.py      # DiscordClient for notifications
├── job_fetch.py           # Main orchestration (refactored)
├── config.json            # User configuration (template)
├── seen_jobs.json         # Auto-generated tracking per profile+location
├── resume.txt             # Existing (user's resume)
└── .github/workflows/
    └── job-alert-{profile}.yml   # One workflow per profile
```

---

## Task 1: Create logger.py

**Files:**
- Create: `logger.py`

**Interfaces:**
- Produces: `setup_logger(level: str) -> logging.Logger`
  - Returns configured logger that all modules use
  - Levels: "INFO", "DEBUG", "VERBOSE" (custom level)
  - Logs with format: `YYYY-MM-DD HH:MM:SS | LEVEL | message`

**Steps:**

- [ ] **Step 1: Write test for logger setup**

Create a test file `tests/test_logger.py`:

```python
import logging
import pytest
from logger import setup_logger

def test_setup_logger_info_level():
    logger = setup_logger("INFO")
    assert logger.level == logging.INFO
    assert logger.name == "job_alert"

def test_setup_logger_debug_level():
    logger = setup_logger("DEBUG")
    assert logger.level == logging.DEBUG

def test_setup_logger_verbose_level():
    """VERBOSE is custom level below DEBUG"""
    logger = setup_logger("VERBOSE")
    assert logger.level == 5  # VERBOSE = 5, below DEBUG (10)

def test_logger_format():
    """Verify log format includes timestamp"""
    logger = setup_logger("INFO")
    handler = logger.handlers[0]
    formatter = handler.formatter
    # Format should contain timestamp, level, message
    assert "%(asctime)s" in formatter._fmt
    assert "%(levelname)s" in formatter._fmt
```

Run: `pytest tests/test_logger.py -v`
Expected: All tests FAIL (logger.py doesn't exist)

- [ ] **Step 2: Implement logger.py**

```python
import logging
import sys

# Define VERBOSE level (below DEBUG)
VERBOSE = 5
logging.addLevelName(VERBOSE, "VERBOSE")

def setup_logger(level: str) -> logging.Logger:
    """
    Setup and return configured logger.
    
    Args:
        level: "INFO", "DEBUG", or "VERBOSE"
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("job_alert")
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Map level string to logging constant
    level_map = {
        "VERBOSE": VERBOSE,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
    }
    
    logger.setLevel(level_map.get(level, logging.INFO))
    
    # Console handler with formatted output
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level_map.get(level, logging.INFO))
    
    # Format: YYYY-MM-DD HH:MM:SS | LEVEL | message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_logger.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add logger.py tests/test_logger.py
git commit -m "feat: add logger with INFO/DEBUG/VERBOSE levels"
```

---

## Task 2: Create config.py - Part 1 (Loading)

**Files:**
- Create: `config.py`

**Interfaces:**
- Produces: `load_config(path: str) -> dict`
  - Reads config.json and returns validated config dict
  - Raises exception if file missing or invalid JSON
- Produces: `validate_config(config: dict) -> bool`
  - Validates required fields exist
  - Returns True if valid, raises ValueError if invalid

**Steps:**

- [ ] **Step 1: Write tests for config loading**

Create `tests/test_config.py`:

```python
import json
import pytest
from pathlib import Path
from config import load_config, validate_config

def test_load_config_valid(tmp_path):
    """Test loading valid config file"""
    config_file = tmp_path / "config.json"
    config_data = {
        "logging": {"level": "INFO"},
        "profiles": {
            "node-backend": {
                "type": "keyword",
                "keywords": ["node", "nodejs"],
                "cron": "0 */4 * * *"
            }
        }
    }
    config_file.write_text(json.dumps(config_data))
    
    result = load_config(str(config_file))
    assert result["logging"]["level"] == "INFO"
    assert "node-backend" in result["profiles"]

def test_load_config_missing_file():
    """Test loading nonexistent file"""
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.json")

def test_load_config_invalid_json(tmp_path):
    """Test loading invalid JSON"""
    config_file = tmp_path / "config.json"
    config_file.write_text("{ invalid json }")
    
    with pytest.raises(json.JSONDecodeError):
        load_config(str(config_file))

def test_validate_config_valid():
    """Test validation of valid config"""
    config = {
        "logging": {"level": "INFO"},
        "profiles": {"test": {"keywords": ["python"]}},
        "discord": {"webhook_url_env": "DISCORD_WEBHOOK_URL"}
    }
    assert validate_config(config) == True

def test_validate_config_missing_logging():
    """Test validation fails without logging"""
    config = {
        "profiles": {"test": {"keywords": ["python"]}}
    }
    with pytest.raises(ValueError, match="logging"):
        validate_config(config)

def test_validate_config_missing_profiles():
    """Test validation fails without profiles"""
    config = {
        "logging": {"level": "INFO"}
    }
    with pytest.raises(ValueError, match="profiles"):
        validate_config(config)
```

Run: `pytest tests/test_config.py -v`
Expected: All tests FAIL (config.py doesn't exist)

- [ ] **Step 2: Implement config.py - load_config function**

```python
import json
from pathlib import Path
from typing import Dict, Any

def load_config(path: str) -> Dict[str, Any]:
    """
    Load and parse config.json.
    
    Args:
        path: Path to config.json
    
    Returns:
        Parsed config dictionary
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    config_path = Path(path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config

def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate config structure and required fields.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        True if valid
    
    Raises:
        ValueError: If required fields missing or invalid
    """
    required_keys = ["logging", "profiles", "discord"]
    
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required field: {key}")
    
    # Validate logging section
    if "level" not in config["logging"]:
        raise ValueError("Missing logging.level")
    
    valid_levels = ["INFO", "DEBUG", "VERBOSE"]
    if config["logging"]["level"] not in valid_levels:
        raise ValueError(f"Invalid logging level: {config['logging']['level']}")
    
    # Validate profiles section (must have at least one)
    if not config["profiles"] or not isinstance(config["profiles"], dict):
        raise ValueError("profiles must be non-empty dict")
    
    # Validate each profile has keywords
    for profile_name, profile_data in config["profiles"].items():
        if "keywords" not in profile_data or not profile_data["keywords"]:
            raise ValueError(f"Profile '{profile_name}' missing keywords array")
    
    # Validate discord section
    if "webhook_url_env" not in config["discord"]:
        raise ValueError("Missing discord.webhook_url_env")
    
    return True
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add config loading and validation"
```

---

## Task 3: Create config.py - Part 2 (Keyword Resolution)

**Files:**
- Modify: `config.py`

**Interfaces:**
- Produces: `resolve_search_keywords(config: dict, profile_name: str, resume_text: str) -> set`
  - Determines keywords based on profile's search_mode
  - Returns set of keywords to search
  - Falls back to resume extraction if needed

**Steps:**

- [ ] **Step 1: Write tests for keyword resolution**

Add to `tests/test_config.py`:

```python
def test_resolve_keywords_from_profile():
    """Test extracting keywords from profile"""
    config = {
        "profiles": {
            "node-backend": {
                "keywords": ["node", "nodejs", "express"],
                "type": "keyword"
            }
        }
    }
    keywords = resolve_search_keywords(config, "node-backend", "")
    assert "node" in keywords
    assert "nodejs" in keywords
    assert "express" in keywords

def test_resolve_keywords_from_resume():
    """Test extracting keywords from resume text"""
    config = {
        "profiles": {
            "resume-search": {
                "type": "keyword",
                "keywords": []  # Empty, should use resume
            }
        }
    }
    resume = "python typescript react postgresql"
    keywords = resolve_search_keywords(config, "resume-search", resume)
    # Should extract from resume
    assert "python" in keywords or "typescript" in keywords

def test_resolve_keywords_missing_profile():
    """Test error on missing profile"""
    config = {"profiles": {}}
    with pytest.raises(ValueError, match="not found"):
        resolve_search_keywords(config, "nonexistent", "")
```

Run: `pytest tests/test_config.py::test_resolve_keywords_from_profile -v`
Expected: FAIL (function not implemented)

- [ ] **Step 2: Add keyword resolution to config.py**

```python
def resolve_search_keywords(config: dict, profile_name: str, resume_text: str) -> set:
    """
    Resolve search keywords for a profile based on search mode.
    
    Args:
        config: Configuration dictionary
        profile_name: Name of profile to search
        resume_text: Lowercased resume text (for resume mode)
    
    Returns:
        Set of keywords to search for
    
    Raises:
        ValueError: If profile not found
    """
    if profile_name not in config["profiles"]:
        raise ValueError(f"Profile '{profile_name}' not found in config")
    
    profile = config["profiles"][profile_name]
    keywords = set()
    
    # Profile defines explicit keywords
    if "keywords" in profile and profile["keywords"]:
        keywords.update(profile["keywords"])
    
    # If no keywords in profile, extract from resume
    if not keywords and resume_text:
        keywords = extract_keywords_from_resume(resume_text)
    
    return keywords

def extract_keywords_from_resume(resume_text: str) -> set:
    """
    Extract tech skills from resume text.
    
    Args:
        resume_text: Lowercased resume text
    
    Returns:
        Set of found skills
    """
    skills = {
        # Languages
        "python", "typescript", "javascript", "java", "c#", "csharp", "dotnet", ".net",
        "golang", "go", "rust", "ruby", "php", "kotlin", "scala", "sql",
        # Backend
        "nodejs", "node.js", "express", "express.js", "asp.net", "asp.net core",
        "fastapi", "django", "flask", "spring", "springboot", "gin", "actix",
        "rest", "rest api", "graphql", "grpc", "microservices",
        # Frontend
        "react", "vue", "angular", "svelte", "nextjs", "next.js", "pwa",
        "react native", "expo", "flutter", "swift", "kotlin",
        # Databases
        "postgresql", "postgres", "mysql", "mongodb", "redis", "cassandra",
        "dynamodb", "cosmosdb", "cosmos db", "elasticsearch", "clickhouse",
        # Cloud
        "aws", "azure", "gcp", "google cloud", "kubernetes", "k8s", "docker",
        "istio", "service mesh", "docker compose", "terraform",
        # Data
        "kafka", "rabbitmq", "kinesis", "spark", "hadoop", "airflow",
        "olap", "apache", "strimzi", "time-series",
        # DevOps
        "ci/cd", "cicd", "jenkins", "gitlab", "github actions", "devops",
        "linux", "bash", "git", "terraform", "ansible",
        # AI/ML
        "rag", "retrieval augmented", "langchain", "llm", "openai", "claude",
        "gemini", "transformers", "pytorch", "tensorflow", "huggingface",
        "machine learning", "deep learning", "nlp",
        # Architecture
        "distributed systems", "system design", "scalability", "microservices",
        "event-driven", "chaos engineering", "multi-tenant",
        # Observability
        "prometheus", "grafana", "datadog", "newrelic", "elastic", "splunk",
        "observability", "monitoring", "logging",
        # Security
        "security", "oauth", "jwt", "tls", "encryption", "penetration testing",
        "https", "https mitm", "ssl", "certificate",
        # Other
        "agile", "scrum", "jira", "confluence", "testing", "unittest",
        "integration testing", "performance testing", "load testing"
    }
    
    found = set()
    for skill in skills:
        if skill in resume_text:
            found.add(skill)
    
    return found
```

- [ ] **Step 3: Run all config tests**

Run: `pytest tests/test_config.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add keyword resolution from profiles and resume"
```

---

## Task 4: Create searchers.py - Part 1 (Base Structure)

**Files:**
- Create: `searchers.py`

**Interfaces:**
- Produces: `class LinkedInSearcher`
  - `search(keywords: list[str], locations: list[str], hours: int, logger) -> list[dict]`
  - Returns list of job dicts with: title, company, link, location, description, posted, posted_datetime, source, skill, portal
- Produces: `class NaukriSearcher`
  - Same search() interface as LinkedInSearcher

**Steps:**

- [ ] **Step 1: Write test for searcher base**

Create `tests/test_searchers.py`:

```python
import pytest
from unittest.mock import Mock, patch
from searchers import LinkedInSearcher, NaukriSearcher

def test_linkedin_searcher_init():
    """Test LinkedInSearcher initializes"""
    logger = Mock()
    searcher = LinkedInSearcher(logger)
    assert searcher.logger == logger

def test_naukri_searcher_init():
    """Test NaukriSearcher initializes"""
    logger = Mock()
    searcher = NaukriSearcher(logger)
    assert searcher.logger == logger

def test_linkedin_search_signature():
    """Test search method accepts required parameters"""
    logger = Mock()
    searcher = LinkedInSearcher(logger)
    # Should accept these parameters (will return empty for now)
    result = searcher.search(
        keywords=["python"],
        locations=["Bangalore"],
        hours=4
    )
    assert isinstance(result, list)

def test_naukri_search_signature():
    """Test search method accepts required parameters"""
    logger = Mock()
    searcher = NaukriSearcher(logger)
    result = searcher.search(
        keywords=["python"],
        locations=["Bangalore"],
        hours=24
    )
    assert isinstance(result, list)
```

Run: `pytest tests/test_searchers.py -v`
Expected: FAIL (searchers.py doesn't exist)

- [ ] **Step 2: Implement searchers.py - Base structure**

```python
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
        # Placeholder - will be filled in Task 5
        return []
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_searchers.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add searchers.py tests/test_searchers.py
git commit -m "feat: add LinkedInSearcher and NaukriSearcher base classes"
```

---

## Task 5: Create searchers.py - Part 2 (LinkedIn Implementation)

**Files:**
- Modify: `searchers.py` (add LinkedIn scraping logic)

**Steps:**

- [ ] **Step 1: Add helper functions to searchers.py**

Add these functions before the searcher classes:

```python
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
```

- [ ] **Step 2: Implement LinkedIn _search_keyword_location**

Replace the placeholder `_search_keyword_location` method in LinkedInSearcher:

```python
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
```

- [ ] **Step 3: Run searcher tests**

Run: `pytest tests/test_searchers.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add searchers.py tests/test_searchers.py
git commit -m "feat: implement LinkedIn job scraping logic"
```

---

## Task 6: Create searchers.py - Part 3 (Naukri Implementation)

**Files:**
- Modify: `searchers.py` (add Naukri scraping logic)

**Steps:**

- [ ] **Step 1: Implement Naukri _search_keyword_location**

Replace the placeholder `_search_keyword_location` method in NaukriSearcher:

```python
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
```

- [ ] **Step 2: Add additional location mappings**

The Naukri implementation handles Bangalore/Bengaluru. Update to handle other Indian locations if needed later (for now India-only is fine per spec).

- [ ] **Step 3: Run searcher tests**

Run: `pytest tests/test_searchers.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add searchers.py
git commit -m "feat: implement Naukri job scraping logic"
```

---

## Task 7: Create discord_client.py

**Files:**
- Create: `discord_client.py`

**Interfaces:**
- Produces: `class DiscordClient`
  - `__init__(webhook_url: str, logger)`
  - `send_jobs(jobs: list[dict], profile_name: str) -> bool`
    - Returns True if sent successfully, False if failed
    - Formats jobs as Discord embeds

**Steps:**

- [ ] **Step 1: Write tests for Discord client**

Create `tests/test_discord.py`:

```python
import pytest
from unittest.mock import Mock, patch
from discord_client import DiscordClient, format_job_embed

def test_discord_client_init():
    """Test DiscordClient initialization"""
    logger = Mock()
    client = DiscordClient("http://example.com/webhook", logger)
    assert client.webhook_url == "http://example.com/webhook"

def test_format_job_embed():
    """Test job formatting as Discord embed"""
    job = {
        "title": "Senior Python Dev",
        "company": "Tech Corp",
        "location": "Bangalore",
        "description": "Build amazing things with Python",
        "link": "https://linkedin.com/job/123",
        "posted": "2 hours ago",
        "skill": "python",
    }
    embed = format_job_embed(job)
    
    assert embed["title"] == "Senior Python Dev"
    assert "Tech Corp" in str(embed["fields"])
    assert "Bangalore" in str(embed["fields"])

def test_discord_send_jobs_empty():
    """Test sending empty job list"""
    logger = Mock()
    client = DiscordClient("http://example.com/webhook", logger)
    result = client.send_jobs([], "test-profile")
    assert result == True  # No error for empty

def test_discord_send_jobs():
    """Test sending jobs to Discord"""
    logger = Mock()
    client = DiscordClient("http://example.com/webhook", logger)
    
    jobs = [{
        "title": "Python Dev",
        "company": "Corp",
        "location": "Bangalore",
        "description": "Python role",
        "link": "https://example.com",
        "posted": "1h ago",
        "skill": "python",
    }]
    
    with patch.object(client, '_send_webhook') as mock_send:
        mock_send.return_value = True
        result = client.send_jobs(jobs, "python-dev")
        assert mock_send.called
```

Run: `pytest tests/test_discord.py -v`
Expected: FAIL (discord_client.py doesn't exist)

- [ ] **Step 2: Implement discord_client.py**

```python
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
```

- [ ] **Step 3: Run Discord tests**

Run: `pytest tests/test_discord.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add discord_client.py tests/test_discord.py
git commit -m "feat: add Discord notification client"
```

---

## Task 8: Create job_fetch.py - Main Orchestration

**Files:**
- Create: `job_fetch.py` (replaces old version)

**Interfaces:**
- CLI: `python job_fetch.py --profile {name} --location {name}`
- Reads: `config.json`, `resume.txt`, `seen_jobs.json`
- Writes: `seen_jobs.json`

**Steps:**

- [ ] **Step 1: Write test for main script**

Create `tests/test_job_fetch.py`:

```python
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

def test_job_fetch_cli_args():
    """Test CLI argument parsing"""
    import sys
    sys.argv = ["job_fetch.py", "--profile", "node-backend", "--location", "Bangalore"]
    
    # Should not raise error
    # (actual test in integration)

def test_load_resume(tmp_path):
    """Test loading resume"""
    resume_file = tmp_path / "resume.txt"
    resume_file.write_text("python typescript react")
    
    # Would be tested in integration
```

- [ ] **Step 2: Implement job_fetch.py**

```python
#!/usr/bin/env python3

import argparse
import json
import os
import hashlib
from pathlib import Path
from typing import Dict, Set
from datetime import datetime

from config import load_config, validate_config, resolve_search_keywords
from logger import setup_logger
from searchers import LinkedInSearcher, NaukriSearcher
from discord_client import DiscordClient

SEEN_JOBS_FILE = Path(__file__).parent / "seen_jobs.json"
RESUME_FILE = Path(__file__).parent / "resume.txt"

def load_resume() -> str:
    """Load and return resume text (lowercased)"""
    if RESUME_FILE.exists():
        return RESUME_FILE.read_text().lower()
    return ""

def load_seen_jobs() -> Dict[str, Set[str]]:
    """Load seen jobs tracking"""
    if SEEN_JOBS_FILE.exists():
        try:
            data = json.loads(SEEN_JOBS_FILE.read_text())
            # Convert lists back to sets
            return {k: set(v) for k, v in data.items()}
        except:
            return {}
    return {}

def save_seen_jobs(seen: Dict[str, Set[str]]):
    """Save seen jobs tracking"""
    # Convert sets to lists for JSON serialization
    data = {k: list(v)[-10000:] for k, v in seen.items()}  # Keep last 10k per profile
    SEEN_JOBS_FILE.write_text(json.dumps(data, indent=2))

def job_id(title: str, company: str, link: str) -> str:
    """Generate unique ID for job"""
    raw = f"{title}|{company}|{link}"
    return hashlib.md5(raw.encode()).hexdigest()

def get_searcher(portal: str, logger):
    """Get appropriate searcher for portal"""
    if portal.lower() == "linkedin":
        return LinkedInSearcher(logger)
    elif portal.lower() == "naukri":
        return NaukriSearcher(logger)
    else:
        raise ValueError(f"Unknown portal: {portal}")

def main():
    parser = argparse.ArgumentParser(description="Job Alert Bot v4")
    parser.add_argument("--profile", required=True, help="Profile name from config")
    parser.add_argument("--location", required=True, help="Location to search")
    parser.add_argument("--config", default="config.json", help="Config file path")
    
    args = parser.parse_args()
    
    # Load config
    try:
        config = load_config(args.config)
        validate_config(config)
    except Exception as e:
        print(f"❌ Config error: {e}")
        exit(1)
    
    # Setup logging
    log_level = config.get("logging", {}).get("level", "INFO")
    logger = setup_logger(log_level)
    
    logger.info(f"🤖 Job Alert Bot - Profile: {args.profile}, Location: {args.location}")
    
    # Validate profile exists
    if args.profile not in config["profiles"]:
        logger.error(f"❌ Profile '{args.profile}' not found in config")
        exit(1)
    
    profile = config["profiles"][args.profile]
    
    # Determine portal (from profile or default to linkedin+naukri)
    portal = profile.get("portal", "all")
    
    # Load resume if needed
    resume_text = load_resume()
    if not resume_text:
        logger.warning("⚠️  resume.txt not found, using profile keywords only")
    else:
        logger.info(f"✅ Resume loaded")
    
    # Resolve keywords
    try:
        keywords = resolve_search_keywords(config, args.profile, resume_text)
        if not keywords:
            logger.error("❌ No keywords found to search")
            exit(1)
        logger.info(f"📊 Keywords: {', '.join(sorted(keywords)[:10])}{'...' if len(keywords) > 10 else ''}")
    except Exception as e:
        logger.error(f"❌ Error resolving keywords: {e}")
        exit(1)
    
    # Get search parameters
    locations = [args.location]
    hours = profile.get("hours", 24)
    
    logger.info(f"🔍 Searching: {hours} hours, {len(keywords)} keywords, location: {args.location}")
    
    # Load seen jobs
    seen = load_seen_jobs()
    profile_location_key = f"{args.profile}:{args.location}"
    if profile_location_key not in seen:
        seen[profile_location_key] = set()
    
    # Search portals
    all_jobs = []
    
    if portal in ["all", "linkedin"]:
        logger.info(f"📍 Searching LinkedIn...")
        linkedin_searcher = LinkedInSearcher(logger)
        linkedin_jobs = linkedin_searcher.search(list(keywords), locations, hours)
        all_jobs.extend(linkedin_jobs)
    
    if portal in ["all", "naukri"]:
        logger.info(f"📍 Searching Naukri...")
        naukri_searcher = NaukriSearcher(logger)
        naukri_jobs = naukri_searcher.search(list(keywords), locations, hours)
        all_jobs.extend(naukri_jobs)
    
    # Filter out seen jobs
    new_jobs = []
    for job in all_jobs:
        jid = job_id(job["title"], job["company"], job["link"])
        if jid not in seen[profile_location_key]:
            seen[profile_location_key].add(jid)
            new_jobs.append(job)
    
    logger.info(f"✅ Found {len(new_jobs)} new jobs")
    
    # Send to Discord
    if new_jobs:
        webhook_url = os.getenv(config["discord"]["webhook_url_env"])
        if not webhook_url:
            logger.error(f"❌ Missing {config['discord']['webhook_url_env']} environment variable")
            exit(1)
        
        discord = DiscordClient(webhook_url, logger)
        discord.send_jobs(new_jobs, args.profile)
    
    # Save seen jobs
    save_seen_jobs(seen)
    
    logger.info(f"✅ Complete at {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run integration tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Test script manually**

```bash
# Test with --help
python job_fetch.py --help
# Expected: Show usage with --profile and --location arguments
```

- [ ] **Step 5: Commit**

```bash
git add job_fetch.py tests/test_job_fetch.py
git commit -m "feat: add main orchestration script with --profile and --location args"
```

---

## Task 9: Create config.json Template

**Files:**
- Create: `config.json`

**Steps:**

- [ ] **Step 1: Create config.json template**

```json
{
  "logging": {
    "level": "INFO",
    "comment": "Options: INFO, DEBUG, VERBOSE"
  },
  "linkedin": {
    "enabled": true,
    "locations": ["Bangalore", "Berlin", "Munich", "Frankfurt"],
    "hours": 4,
    "comment": "LinkedIn specific configuration"
  },
  "naukri": {
    "enabled": true,
    "locations": ["Bangalore"],
    "hours": 24,
    "comment": "Naukri specific configuration (India only)"
  },
  "profiles": {
    "node-backend": {
      "type": "keyword",
      "keywords": ["node", "nodejs", "express", "javascript", "typescript"],
      "description": "Backend roles using Node.js",
      "cron": "0 */4 * * *",
      "portal": "all",
      "comment": "Optional: seniority, min_years fields can be added"
    },
    "python-fullstack": {
      "type": "keyword",
      "keywords": ["python", "django", "fastapi", "react", "postgresql"],
      "description": "Python full-stack developer roles",
      "cron": "0 0 * * *",
      "portal": "all"
    },
    "senior-node": {
      "type": "keyword",
      "keywords": ["node", "nodejs", "express"],
      "description": "Senior Node.js roles (with seniority filter)",
      "seniority": ["senior", "lead", "principal"],
      "min_years": 5,
      "cron": "0 0 * * *",
      "portal": "all"
    }
  },
  "discord": {
    "webhook_url_env": "DISCORD_WEBHOOK_URL",
    "comment": "Discord webhook URL read from environment variable"
  }
}
```

- [ ] **Step 2: Verify config.json is valid**

```bash
python -c "import json; json.load(open('config.json'))"
# Expected: No output (valid JSON)
```

- [ ] **Step 3: Commit**

```bash
git add config.json
git commit -m "feat: add config.json template with example profiles"
```

---

## Task 10: Create GitHub Actions Workflow Templates

**Files:**
- Create: `.github/workflows/job-alert-node-backend.yml`
- Create: `.github/workflows/job-alert-python-fullstack.yml`
- Create: `.github/workflows/job-alert-senior-node.yml`

**Steps:**

- [ ] **Step 1: Create LinkedIn + multi-location workflow**

Create `.github/workflows/job-alert-node-backend.yml`:

```yaml
name: Job Alert - node-backend

on:
  schedule:
    # Every 4 hours: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
    - cron: '0 */4 * * *'
  workflow_dispatch:

jobs:
  search:
    strategy:
      matrix:
        location: ["Bangalore", "Berlin"]
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests beautifulsoup4
      
      - name: Search for jobs
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: python job_fetch.py --profile node-backend --location "${{ matrix.location }}"
```

- [ ] **Step 2: Create daily profile workflow**

Create `.github/workflows/job-alert-python-fullstack.yml`:

```yaml
name: Job Alert - python-fullstack

on:
  schedule:
    # Daily at midnight UTC
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  search:
    strategy:
      matrix:
        location: ["Bangalore"]
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests beautifulsoup4
      
      - name: Search for jobs
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: python job_fetch.py --profile python-fullstack --location "${{ matrix.location }}"
```

- [ ] **Step 3: Create senior role workflow**

Create `.github/workflows/job-alert-senior-node.yml`:

```yaml
name: Job Alert - senior-node

on:
  schedule:
    # Daily at midnight UTC
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  search:
    strategy:
      matrix:
        location: ["Bangalore", "Berlin"]
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests beautifulsoup4
      
      - name: Search for jobs
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: python job_fetch.py --profile senior-node --location "${{ matrix.location }}"
```

- [ ] **Step 4: Commit workflows**

```bash
git add .github/workflows/
git commit -m "feat: add GitHub Actions workflows for each profile with location parallelization"
```

---

## Task 11: Update seen_jobs.json Structure

**Files:**
- Modify: `seen_jobs.json` (document structure, will be auto-generated)

**Steps:**

- [ ] **Step 1: Document the new structure**

The `seen_jobs.json` file will be auto-generated on first run. Structure:

```json
{
  "node-backend:Bangalore": [
    "abc123def456",
    "xyz789uvw456"
  ],
  "node-backend:Berlin": [
    "hash1",
    "hash2"
  ],
  "python-fullstack:Bangalore": [
    "hash3"
  ]
}
```

Key points:
- Format: `"{profile_name}:{location}": [list of job hashes]`
- Each hash is MD5(title + company + link)
- Keeps last 10,000 per profile:location combo
- Auto-created if missing

- [ ] **Step 2: Commit documentation**

```bash
git add docs/superpowers/plans/2026-07-19-job-alert-modular.md
git commit -m "docs: document seen_jobs.json structure for per-profile tracking"
```

---

## Task 12: Manual Testing - Single Location Search

**Files:**
- Test: All modules end-to-end

**Steps:**

- [ ] **Step 1: Test config loading and validation**

```bash
python -c "
from config import load_config, validate_config
config = load_config('config.json')
validate_config(config)
print('✅ Config loaded and validated')
"
# Expected: ✅ Config loaded and validated
```

- [ ] **Step 2: Test resume loading**

```bash
python -c "
from job_fetch import load_resume
resume = load_resume()
print(f'✅ Resume loaded ({len(resume)} chars)')
"
# Expected: ✅ Resume loaded (...) (or warning if no resume)
```

- [ ] **Step 3: Test keyword resolution**

```bash
python -c "
from config import load_config, resolve_search_keywords
from job_fetch import load_resume
config = load_config('config.json')
resume = load_resume()
keywords = resolve_search_keywords(config, 'node-backend', resume)
print(f'✅ Keywords resolved: {len(keywords)} keywords')
print(f'   Sample: {list(keywords)[:5]}')
"
# Expected: ✅ Keywords resolved: N keywords
```

- [ ] **Step 4: Test single location search (Bangalore)**

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/test"
python job_fetch.py --profile node-backend --location Bangalore
```

Expected output:
```
2026-07-19 15:30:00 | INFO  | 🤖 Job Alert Bot - Profile: node-backend, Location: Bangalore
2026-07-19 15:30:01 | INFO  | ✅ Resume loaded
2026-07-19 15:30:02 | INFO  | 📊 Keywords: node, nodejs, express, ...
2026-07-19 15:30:03 | INFO  | 🔍 Searching: 4 hours, N keywords, location: Bangalore
2026-07-19 15:30:04 | INFO  | 📍 Searching LinkedIn...
2026-07-19 15:30:10 | INFO  | ✅ Found X new jobs
2026-07-19 15:30:11 | INFO  | ✅ Complete...
```

- [ ] **Step 5: Verify seen_jobs.json was created**

```bash
python -c "
import json
data = json.load(open('seen_jobs.json'))
print('✅ seen_jobs.json created')
print(f'   Keys: {list(data.keys())}')
"
# Expected: ✅ seen_jobs.json created
```

- [ ] **Step 6: Commit successful test**

```bash
git add seen_jobs.json
git commit -m "test: verify single location search works"
```

---

## Task 13: Manual Testing - Multiple Profiles

**Files:**
- Test: Multiple profiles

**Steps:**

- [ ] **Step 1: Test python-fullstack profile**

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/test"
python job_fetch.py --profile python-fullstack --location Bangalore
```

Expected: Similar output to node-backend, but with different keywords

- [ ] **Step 2: Test senior-node profile with filters**

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/test"
python job_fetch.py --profile senior-node --location Berlin
```

Expected: 
- Shows seniority filter in debug logs
- Skips jobs without "senior", "lead", "principal" in title/description
- Still finds jobs without the filter fields (graceful degradation)

- [ ] **Step 3: Verify seen_jobs.json has multiple profiles**

```bash
python -c "
import json
data = json.load(open('seen_jobs.json'))
print(f'✅ Profiles tracked: {list(data.keys())}')
"
# Expected: Shows all profile:location combinations
```

- [ ] **Step 4: Run script twice, verify no duplicates**

Run same command twice, second run should show 0 new jobs or only jobs newer than first run.

- [ ] **Step 5: Commit test results**

```bash
git commit -am "test: verify multiple profile searches and deduplication"
```

---

## Task 14: Manual Testing - GitHub Actions Workflows

**Files:**
- Test: Workflow execution

**Steps:**

- [ ] **Step 1: Trigger workflow manually**

In GitHub repo:
1. Go to "Actions"
2. Select "Job Alert - node-backend"
3. Click "Run workflow"
4. Select branch and run

Expected: 
- Workflow runs for both Bangalore and Berlin in parallel
- Both jobs complete successfully
- Discord receives notifications

- [ ] **Step 2: Verify workflow logs**

Click on workflow run, check logs for each location job:
- Should show search progress
- Should show number of jobs found
- Should show Discord send success

- [ ] **Step 3: Test workflow cron schedules**

Verify the cron expressions in workflows match config.json:
- node-backend: `0 */4 * * *` (every 4 hours)
- python-fullstack: `0 0 * * *` (daily)
- senior-node: `0 0 * * *` (daily)

- [ ] **Step 4: Commit workflow verification**

```bash
git commit -am "test: verify GitHub Actions workflows execute correctly"
```

---

## Final Verification Checklist

Before marking complete, verify:

- [ ] All modules created and tested (config.py, logger.py, searchers.py, discord_client.py, job_fetch.py)
- [ ] config.json template with example profiles
- [ ] GitHub Actions workflows created (one per profile)
- [ ] Logging works at INFO/DEBUG/VERBOSE levels
- [ ] Single location search works
- [ ] Multiple profiles work independently
- [ ] seen_jobs.json tracks per profile+location (no duplicates)
- [ ] Workflow matrix parallelizes locations
- [ ] Discord notifications send successfully
- [ ] All code committed with clear messages

---

## Tech Stack Summary

- **Python 3.11** - Core language
- **BeautifulSoup4** - HTML parsing (LinkedIn, Naukri)
- **Requests** - HTTP client for scraping and Discord webhook
- **GitHub Actions** - Workflow orchestration
- **Discord Webhooks** - Notifications
- **JSON** - Config and tracking storage
- **pytest** - Testing (optional for manual testing)
