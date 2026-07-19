# seen_jobs.json Structure Documentation

## Overview

`seen_jobs.json` is a persistent tracking file that maintains a record of all job postings that have been seen/notified for each profile and location combination. This prevents duplicate notifications for the same job posting.

## File Format

```json
{
  "profile-name:location": [
    "hash1",
    "hash2",
    "hash3"
  ],
  "another-profile:location": [
    "hash4",
    "hash5"
  ]
}
```

## Structure Details

### Key Format
- Format: `{profile_name}:{location}`
- Example: `"node-backend:Bangalore"`, `"python-fullstack:Berlin"`
- Profile name comes from the `config.json` profiles section
- Location is the search location passed to the application

### Values
- Each key maps to an array of job hashes
- Hashes are stored in JSON as strings (lists, not sets)
- Upon loading, these are converted to Python sets for O(1) lookups

### Hash Format
- **Algorithm**: MD5
- **Input**: `{title}|{company}|{link}`
- **Output**: 32-character hexadecimal string
- **Purpose**: Uniquely identify a job posting
- **Generation**: See `job_fetch.py::job_id()` function

### Example Calculation
```
Title: "Python Developer"
Company: "Tech Corp"
Link: "https://example.com/job/123"
Raw: "Python Developer|Tech Corp|https://example.com/job/123"
Hash: MD5(raw) = "a1b2c3d4e5f6..."
```

## Key Characteristics

### Automatic Creation
- File is auto-created when `save_seen_jobs()` is first called
- If the file doesn't exist, `load_seen_jobs()` returns an empty dictionary
- The application creates the profile:location key on first run

### Size Management
- Keeps last **10,000 hashes** per profile:location combination
- When saving, if a profile:location has more than 10,000 hashes, only the last 10,000 are kept
- This prevents unbounded file growth

### Duplicate Prevention
- When a new job search is performed:
  1. All found jobs are hashed using `job_id()`
  2. Hash is checked against the profile:location set
  3. If hash exists → job is marked as seen (not notified)
  4. If hash is new → job is marked for notification
  5. After notification, hash is added to the tracking set

### Data Format Conversion
- **Saving**: Sets are converted to lists for JSON serialization
- **Loading**: Lists are converted back to sets for efficient lookups
- This is handled automatically by `save_seen_jobs()` and `load_seen_jobs()`

## File Location
- **Path**: `{project_root}/seen_jobs.json`
- **Determined by**: `SEEN_JOBS_FILE = Path(__file__).parent / "seen_jobs.json"` in `job_fetch.py`

## Implementation

### Loading
```python
def load_seen_jobs() -> Dict[str, Set[str]]:
    """Load seen jobs tracking from JSON file."""
    if SEEN_JOBS_FILE.exists():
        try:
            data = json.loads(SEEN_JOBS_FILE.read_text())
            # Convert lists back to sets for O(1) lookups
            return {k: set(v) for k, v in data.items()}
        except Exception:
            return {}
    return {}
```

### Saving
```python
def save_seen_jobs(seen: Dict[str, Set[str]]):
    """Save seen jobs tracking to JSON file."""
    # Convert sets to lists for JSON serialization
    # Keep last 10k per profile to avoid unbounded growth
    data = {k: list(v)[-10000:] for k, v in seen.items()}
    SEEN_JOBS_FILE.write_text(json.dumps(data, indent=2))
```

### Usage in Main Flow
1. **Load**: `seen = load_seen_jobs()` - loads entire tracking file
2. **Initialize key**: If `profile:location` key missing, create empty set
3. **Check jobs**: For each job found, compute hash and check if in seen set
4. **Track new**: Add hash for new jobs to the set
5. **Save**: `save_seen_jobs(seen)` - persist updated state

## Workflow Example

```
Config: profile="python-fullstack", location="Bangalore"

1. Load seen jobs from file:
   seen = {
     "python-fullstack:Bangalore": {"abc123...", "def456..."}
   }

2. Search for new jobs - get results:
   [{title: "Jr Python Dev", company: "TechCorp", link: "...123"},
    {title: "Sr Python Dev", company: "StartupXYZ", link: "...456"},
    {title: "Python Dev", company: "BigCorp", link: "...789"}]

3. Compute hashes:
   job1_hash = MD5("Jr Python Dev|TechCorp|...123") = "abc123..." ✓ seen
   job2_hash = MD5("Sr Python Dev|StartupXYZ|...456") = "def456..." ✓ seen
   job3_hash = MD5("Python Dev|BigCorp|...789") = "new789..." ✗ not seen

4. Filter and notify:
   - Only job3 is new, mark for Discord notification
   - Add "new789..." to seen["python-fullstack:Bangalore"]

5. Save state:
   seen = {
     "python-fullstack:Bangalore": {"abc123...", "def456...", "new789..."}
   }
```

## Testing

See `tests/test_job_fetch.py::test_save_and_load_seen_jobs()` for validation that:
- Save/load cycle preserves data
- Sets are correctly converted to lists and back
- Multiple profile:location combinations can coexist
- File is properly formatted as valid JSON

## Notes

- The structure supports multiple profiles and locations independently
- Each profile:location combination maintains its own seen job history
- No cross-profile sharing of seen jobs (intentional)
- Hash collisions are theoretically possible but extremely rare with MD5
