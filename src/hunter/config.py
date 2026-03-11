"""Configuration loader for HUNTER-v2."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_config(config_path: str | None = None) -> dict:
    """Load settings from YAML config file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
    else:
        config_path = Path(config_path)

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_env() -> dict:
    """Load environment variables from .env file."""
    load_dotenv()
    return {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "twitter_api_key": os.getenv("TWITTER_API_KEY", ""),
        "twitter_api_secret": os.getenv("TWITTER_API_SECRET", ""),
        "twitter_access_token": os.getenv("TWITTER_ACCESS_TOKEN", ""),
        "twitter_access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET", ""),
        "twitter_bearer_token": os.getenv("TWITTER_BEARER_TOKEN", ""),
        "sociavault_api_key": os.getenv("SOCIAVAULT_API_KEY", ""),
        "twitterapi_io_key": os.getenv("TWITTERAPI_IO_KEY", ""),
        "reader_provider": os.getenv("READER_PROVIDER", "sociavault"),
    }


class Settings:
    """Application settings combining config file and environment variables."""

    def __init__(self, config_path: str | None = None):
        self.config = load_config(config_path)
        self.env = load_env()

    @property
    def anthropic_api_key(self) -> str:
        return self.env["anthropic_api_key"]

    @property
    def reader_provider(self) -> str:
        return self.env.get("reader_provider") or self.config.get("reader", {}).get("provider", "sociavault")

    @property
    def posting(self) -> dict:
        return self.config.get("posting", {})

    @property
    def content(self) -> dict:
        return self.config.get("content", {})

    @property
    def agent_model(self) -> str:
        return self.config.get("agents", {}).get("model", "claude-sonnet-4-6")

    @property
    def competitors(self) -> list[str]:
        return self.config.get("competitors", [])

    @property
    def monthly_budget_usd(self) -> float:
        return self.config.get("reader", {}).get("monthly_budget_usd", 5.0)
