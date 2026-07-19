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

def test_resolve_keywords_from_profile():
    """Test extracting keywords from profile"""
    from config import resolve_search_keywords
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
    from config import resolve_search_keywords
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
    from config import resolve_search_keywords
    config = {"profiles": {}}
    with pytest.raises(ValueError, match="not found"):
        resolve_search_keywords(config, "nonexistent", "")
