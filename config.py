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
