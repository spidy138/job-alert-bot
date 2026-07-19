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
        "source": "LinkedIn",
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
        "source": "LinkedIn",
    }]

    with patch.object(client, '_send_webhook') as mock_send:
        mock_send.return_value = True
        result = client.send_jobs(jobs, "python-dev")
        assert mock_send.called
