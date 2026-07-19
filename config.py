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
