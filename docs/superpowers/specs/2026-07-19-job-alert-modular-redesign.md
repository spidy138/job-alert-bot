# Job Alert Bot v4: Modular Redesign with Independent Portal Scheduling

**Date:** 2026-07-19  
**Status:** Design Approved  
**Author:** Claude Code

## Overview

Enhance the existing job_fetch.py script to support:
- **Independent portal scheduling** - LinkedIn runs every 4 hours, Naukri runs daily
- **Per-portal configuration** - Different locations and time windows for each job board
- **Modular architecture** - Clean separation of concerns for maintainability
- **Enhanced debugging** - Configurable logging (INFO/DEBUG/VERBOSE) with clear output
- **Parallel GitHub Actions** - Non-blocking independent workflows

## Problem Statement

Current script (`job_fetch.py`):
- Hardcoded 6-hour filter for both portals
- Single GitHub Actions workflow running both sequentially (inefficient)
- All logic in one large file (harder to debug/maintain)
- Limited logging (makes troubleshooting difficult)
- No per-portal configuration flexibility

## Solution: Modular Architecture with Independent Workflows

### Architecture

```
job_fetch/
├── config.py                      # Config loading & validation
├── logger.py                      # Centralized logging setup
├── searchers.py                   # Portal-specific search classes
├── discord_client.py              # Discord notification handling
├── job_fetch.py                   # Main orchestration (--portal arg)
├── config.json                    # User configuration (new)
├── seen_jobs.json                 # Per-portal job tracking (auto-generated)
├── resume.txt                     # User resume (existing)
└── .github/workflows/
    ├── job-alert-linkedin.yml     # Runs every 4 hours
    └── job-alert-naukri.yml       # Runs every 24 hours
```

### Module Responsibilities

**config.py**
- Load config.json and validate schema
- Fail fast if required fields missing or invalid
- Provide `load_config(path)` returning validated config dict
- Provide `get_portal_config(portal_name)` to fetch LinkedIn or Naukri settings

**logger.py**
- Setup logger with configurable level: INFO, DEBUG, VERBOSE
- Provide `setup_logger(level_string)` function
- All modules use this logger (no direct print statements)
- INFO: High-level progress (skills loaded, jobs found, sent to Discord)
- DEBUG: API details (HTTP status codes, filtering steps)
- VERBOSE: Per-job details (every job checked, exact regex matches, time calculations)

**searchers.py**
- `LinkedInSearcher` class with `search(keywords, locations, hours)` method
- `NaukriSearcher` class with `search(keywords, locations, hours)` method
- Keywords source: Resume extraction OR config-defined profiles OR both (based on search_mode)
- Both return list of new Job objects (not previously seen)
- Job filtering: Apply optional filters (seniority, min_years) only if defined in profile
- Use logger for all outputs
- Handle network errors gracefully (log, continue, don't crash)

**discord_client.py**
- `DiscordClient` class with `send_jobs(jobs, portal_name)` method
- Format jobs into embeds with title, company, location, link, posting time
- Handle Discord API errors (log error but don't fail the run)

**job_fetch.py** (main)
- Entry point with `--portal [linkedin|naukri|all]` argument
- Load config.json and validate
- Load resume.txt (for resume extraction if needed)
- For selected portal(s):
  - Get search_mode (resume/profiles/both)
  - Determine keywords: resume extraction, profile keywords, or both
  - Instantiate searcher (LinkedInSearcher or NaukriSearcher)
  - Call searcher with keywords + portal-specific {locations, hours, profile_filters}
  - Send results to Discord
  - Update seen_jobs.json (tracking per portal)

### Configuration File (config.json)

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
    "search_mode": "profiles",
    "search_profiles": ["node-backend", "fullstack"]
  },
  "naukri": {
    "enabled": true,
    "locations": ["Bangalore"],
    "hours": 24,
    "search_mode": "resume",
    "search_profiles": []
  },
  "profiles": {
    "node-backend": {
      "type": "keyword",
      "keywords": ["node", "nodejs", "express", "javascript", "typescript"],
      "description": "Backend roles using Node.js"
    },
    "fullstack": {
      "type": "keyword",
      "keywords": ["fullstack", "react", "python", "postgresql", "rest api"],
      "description": "Full-stack developer roles"
    },
    "senior-node": {
      "type": "keyword",
      "keywords": ["node", "nodejs"],
      "seniority": ["senior", "lead"],
      "min_years": 5
    }
  },
  "discord": {
    "webhook_url_env": "DISCORD_WEBHOOK_URL",
    "comment": "Read from environment variable for security"
  }
}
```

**Search Modes:**
- `"resume"` - Extract keywords from resume.txt (existing behavior)
- `"profiles"` - Use only keywords from defined profiles
- `"both"` - Combine resume keywords + profile keywords

**Profile Structure:**
- `keywords` (required) - List of keywords to search
- `type` (optional, default "keyword") - Currently "keyword", later "profile" for seniority/experience filtering
- `description` (optional) - Human-readable description
- `seniority` (optional) - Array like ["senior", "lead"] - if missing, filter is skipped
- `min_years` / `max_years` (optional) - Experience filters - if missing, filter is skipped
- **All optional fields**: If not defined, that filter is simply skipped (no crash)

### Data Flow

**LinkedIn Search** (`python job_fetch.py --portal linkedin`):
1. Load config.json → Extract LinkedIn: {locations, hours, search_mode, search_profiles}
2. Determine search keywords:
   - If search_mode="resume": Extract skills from resume.txt
   - If search_mode="profiles": Get keywords from config.profiles[profile_name] for each profile
   - If search_mode="both": Combine resume skills + profile keywords
3. Create LinkedInSearcher(logger)
4. searcher.search(keywords, locations, hours) → List[Job]
5. For each job: check against seen_jobs.json["linkedin"]
6. Format & send to Discord (include which profile matched, if applicable)
7. Update seen_jobs.json["linkedin"] with new job IDs
8. Exit

**Naukri Search** (`python job_fetch.py --portal naukri`):
1. Load config.json → Extract Naukri: {locations, hours, search_mode, search_profiles}
2. Determine search keywords (same logic as LinkedIn)
3. Create NaukriSearcher(logger)
4. searcher.search(keywords, locations, hours) → List[Job]
5. For each job: check against seen_jobs.json["naukri"]
6. Format & send to Discord (include which profile matched, if applicable)
7. Update seen_jobs.json["naukri"] with new job IDs
8. Exit

Seen jobs are tracked per-portal so runs don't interfere with each other.

**Profile Filtering** (if defined):
- Seniority filter: Only if "seniority" field exists in profile
- Experience filter: Only if "min_years" or "max_years" field exists
- Missing optional fields: Filter is skipped (graceful degradation)

### Error Handling

**Startup (Fail Fast)**
- Missing config.json → Log error, exit(1)
- Invalid config schema → Log which field invalid, exit(1)
- Missing resume.txt → Log error, exit(1)
- Missing DISCORD_WEBHOOK_URL env var → Log error, exit(1)
- Unknown --portal argument → Log error, exit(1)

**Runtime (Log & Continue)**
- Network timeout on LinkedIn/Naukri → Log warning, skip location, continue
- Discord webhook fails → Log error, jobs were found (notification is secondary)
- Invalid job data (missing title, link) → Log at VERBOSE, skip job, continue
- Malformed JSON in seen_jobs.json → Log warning, rebuild from scratch

### Logging Strategy

**INFO Level Output** (default):
```
2026-07-19 14:32:00 | INFO  | 🤖 Job Alert Bot - LinkedIn
2026-07-19 14:32:01 | INFO  | ✅ Config loaded
2026-07-19 14:32:02 | INFO  | ✅ Resume loaded (23 skills)
2026-07-19 14:32:03 | INFO  | 🔍 Searching Bangalore...
2026-07-19 14:32:05 | INFO  | ✅ Found 3 new jobs
2026-07-19 14:32:06 | INFO  | 📤 Sending Discord...
2026-07-19 14:32:07 | INFO  | ✅ Complete
```

**DEBUG Level Output** (add):
```
2026-07-19 14:32:03 | DEBUG | GET https://linkedin.com/jobs?keywords=python&location=Bangalore
2026-07-19 14:32:04 | DEBUG | HTTP 200, 45 results found
2026-07-19 14:32:04 | DEBUG | Filtering: location=Bangalore, hours=4, English text only
```

**VERBOSE Level Output** (add):
```
2026-07-19 14:32:04 | VERBOSE | Job: "Senior Python Dev" - Posted 2h ago (within 4h window) ✓
2026-07-19 14:32:04 | VERBOSE | Job: "Java Developer" - Non-English text ✗
2026-07-19 14:32:04 | VERBOSE | Job: "DevOps Engineer" - Posted 8h ago (outside 4h window) ✗
```

### GitHub Actions Workflows

Each profile gets its own workflow file. Locations within each profile run in parallel via GitHub Actions matrix.

**Example: job-alert-node-backend.yml** (every 4 hours):
```yaml
name: Job Alert - node-backend

on:
  schedule:
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
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install requests beautifulsoup4
      - env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: python job_fetch.py --profile node-backend --location ${{ matrix.location }}
```

**Example: job-alert-fullstack.yml** (daily):
```yaml
name: Job Alert - fullstack

on:
  schedule:
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
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install requests beautifulsoup4
      - env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: python job_fetch.py --profile fullstack --location ${{ matrix.location }}
```

**Workflow structure:**
- One workflow file per profile: `.github/workflows/job-alert-{profile-name}.yml`
- Cron schedule defined in config.json, mirrored in workflow file
- Matrix strategy parallelizes location searches (multiple locations run simultaneously)
- All profiles run independently on their own schedules (non-blocking)
- Manual trigger available for each workflow

**CLI arguments updated:**
- `--profile {profile-name}` — Required, selects which profile to search
- `--location {location-name}` — Required, passed by GitHub Actions matrix
- Example: `python job_fetch.py --profile node-backend --location Bangalore`

### Seen Jobs Tracking

**Structure** (seen_jobs.json):
```json
{
  "node-backend": {
    "Bangalore": ["hash1_id", "hash2_id"],
    "Berlin": ["hash3_id"]
  },
  "fullstack": {
    "Bangalore": ["hash4_id"]
  }
}
```

- Each profile + location combination has independent tracking
- Use MD5(title + company + link) as unique ID
- Prevents duplicate notifications across runs
- Keep last 10,000 per profile-location to prevent unbounded growth

### Success Criteria

✅ Config file loaded successfully on startup  
✅ Search mode resolved: resume extraction, profiles, or both  
✅ Keywords collected from selected profile  
✅ Single location searches isolated (--profile and --location args)  
✅ New jobs sent to Discord with posting time and profile name  
✅ Seen jobs tracked per profile + location (no duplicates)  
✅ INFO level logs show progress at high level  
✅ DEBUG level logs show API details  
✅ VERBOSE level logs show filtering decisions  
✅ Profiles with optional filters (seniority, min_years) gracefully skip missing fields  
✅ Each profile has independent GitHub Actions workflow  
✅ Locations within profile run in parallel (GitHub Actions matrix)  
✅ All profiles run independently on their own schedules (non-blocking)  
✅ Manual trigger available for each workflow  
✅ Network errors logged, don't crash  
✅ Discord errors logged, don't fail the run  

## Implementation Order

1. Create config.py (load & validate config.json, resolve search keywords)
2. Create logger.py (logging setup with INFO/DEBUG/VERBOSE)
3. Refactor searchers.py (LinkedIn & Naukri classes, handle optional profile filters)
4. Create discord_client.py (notification handler)
5. Refactor job_fetch.py (orchestration with --profile and --location args)
6. Create config.json template (with example profiles and cron schedules)
7. Create .github/workflows/ (one workflow file per profile, matrix for locations)
8. Update seen_jobs.json structure (per profile + location)
9. Test all paths (single location, multiple locations, profile with/without filters)

## Backward Compatibility

This is a breaking change:
- Old job_fetch.py replaced with new modular version
- Requires config.json with profiles (no fallback to old behavior)
- CLI arguments --profile and --location required
- Existing seen_jobs.json will be rebuilt on first run (new structure: profile + location)
- GitHub Actions workflows need to be created per profile (no single unified workflow)

## Out of Scope

- Adding new job portals (IndeedHackingJobs, etc.) - can be added later
- Email notifications (Discord only for now)
- Web UI dashboard (Discord notifications sufficient)
- Job filtering by salary/seniority level (can add to config later)
- Resume keyword weighting (all skills treated equally)
