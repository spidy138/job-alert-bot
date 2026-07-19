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
