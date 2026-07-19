import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from searchers import LinkedInSearcher, NaukriSearcher, parse_posting_time, is_posted_within_hours, is_english, is_relevant_location

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


def test_parse_posting_time_hours_ago():
    """Test parsing hours ago format"""
    result = parse_posting_time("2 hours ago")
    assert result is not None
    now = datetime.now()
    diff = (now - result).total_seconds()
    # Should be approximately 2 hours (7200 seconds), allow 2 minute tolerance
    assert 7080 <= diff <= 7320


def test_parse_posting_time_just_now():
    """Test parsing just now"""
    result = parse_posting_time("just now")
    assert result is not None
    now = datetime.now()
    assert (now - result).total_seconds() < 10


def test_is_posted_within_hours():
    """Test time window check"""
    # Posted 2 hours ago, should be within 4 hours
    posted_time = datetime.now() - timedelta(hours=2)
    assert is_posted_within_hours(posted_time, 4) == True
    # Posted 5 hours ago, should NOT be within 4 hours
    old_time = datetime.now() - timedelta(hours=5)
    assert is_posted_within_hours(old_time, 4) == False


def test_is_english_text():
    """Test English detection"""
    assert is_english("This is English text") == True
    assert is_english("यह हिंदी है") == False


def test_is_relevant_location():
    """Test location matching"""
    assert is_relevant_location("Bangalore, India", "Bangalore") == True
    assert is_relevant_location("Berlin, Germany", "Berlin") == True
    assert is_relevant_location("Delhi", "Bangalore") == False
