import pytest
from pathlib import Path
import hashlib
import sys
import os

# Add parent directory to path to import job_fetch
sys.path.insert(0, str(Path(__file__).parent.parent))

from job_fetch import job_id, load_resume, save_seen_jobs, load_seen_jobs


def test_job_id_generation():
    """Test job ID generation creates consistent MD5 hashes"""
    title = "Python Developer"
    company = "Tech Corp"
    link = "https://example.com/job/123"

    id1 = job_id(title, company, link)
    id2 = job_id(title, company, link)

    # Should be consistent
    assert id1 == id2
    # Should be 32-char hex (MD5)
    assert len(id1) == 32
    assert all(c in "0123456789abcdef" for c in id1)


def test_job_id_different_inputs():
    """Test that different job inputs produce different IDs"""
    id1 = job_id("Python Developer", "Tech Corp", "https://example.com/job/123")
    id2 = job_id("Python Developer", "Tech Corp", "https://example.com/job/124")
    id3 = job_id("Java Developer", "Tech Corp", "https://example.com/job/123")

    # All should be different
    assert id1 != id2
    assert id1 != id3
    assert id2 != id3


def test_load_resume():
    """Test loading resume (or empty if not found)"""
    # This should not crash even if resume.txt doesn't exist
    result = load_resume()

    # Should return a string (could be empty)
    assert isinstance(result, str)

    # If resume.txt exists, it should be lowercased
    if result:
        # Check that it's in lowercase if it contains letters
        assert result == result.lower()


def test_save_and_load_seen_jobs(tmp_path, monkeypatch):
    """Test save and load seen jobs cycle"""
    # Mock file path to temp directory
    test_seen_file = tmp_path / "seen_jobs.json"
    monkeypatch.setattr("job_fetch.SEEN_JOBS_FILE", test_seen_file)

    # Save test data
    test_seen = {
        "node-backend:Bangalore": {"hash1", "hash2", "hash3"},
        "python-fullstack:Bangalore": {"hash4"},
    }
    save_seen_jobs(test_seen)

    # Load and verify
    loaded = load_seen_jobs()
    assert "node-backend:Bangalore" in loaded
    assert "hash1" in loaded["node-backend:Bangalore"]
    assert "hash2" in loaded["node-backend:Bangalore"]
    assert len(loaded["python-fullstack:Bangalore"]) == 1
