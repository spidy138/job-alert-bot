import pytest
from pathlib import Path
import hashlib
import sys
import os

# Add parent directory to path to import job_fetch
sys.path.insert(0, str(Path(__file__).parent.parent))

from job_fetch import job_id, load_resume


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
