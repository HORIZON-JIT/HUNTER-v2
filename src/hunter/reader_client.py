"""Third-party API client for reading/analyzing tweets.

Supports SociaVault and TwitterAPI.io as backends.
"""

import requests

from hunter.config import Settings
from hunter.db import get_monthly_api_cost, log_api_usage


class ReaderClient:
    """Unified client for reading tweets via third-party APIs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.reader_provider
        self.budget_limit = settings.monthly_budget_usd

        if self.provider == "sociavault":
            self._api_key = settings.env.get("sociavault_api_key", "")
            self._base_url = "https://api.sociavault.com/v1/scrape/twitter"
        elif self.provider == "twitterapi_io":
            self._api_key = settings.env.get("twitterapi_io_key", "")
            self._base_url = "https://api.twitterapi.io/twitter"
        else:
            raise ValueError(f"Unknown reader provider: {self.provider}")

    def _check_budget(self, estimated_cost: float) -> None:
        """Check if we're within the monthly budget."""
        current_cost = get_monthly_api_cost(self.provider)
        if current_cost + estimated_cost > self.budget_limit:
            raise RuntimeError(
                f"Monthly budget limit reached. "
                f"Current: ${current_cost:.2f}, Limit: ${self.budget_limit:.2f}"
            )

    def _headers(self) -> dict:
        return {"X-API-Key": self._api_key}

    # --- SociaVault methods ---

    def _sociavault_search(self, query: str, count: int = 20) -> list[dict]:
        self._check_budget(0.01)
        resp = requests.get(
            f"{self._base_url}/search",
            params={"q": query, "limit": count},
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        cost = count / 10000  # ~$0.001 per tweet
        log_api_usage("sociavault", "search", cost_usd=cost)
        return resp.json().get("data", resp.json().get("results", []))

    def _sociavault_user_tweets(self, username: str, count: int = 20) -> list[dict]:
        self._check_budget(0.01)
        resp = requests.get(
            f"{self._base_url}/user-tweets",
            params={"username": username, "count": count},
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        cost = count / 10000
        log_api_usage("sociavault", "user_tweets", cost_usd=cost)
        return resp.json().get("data", resp.json().get("results", []))

    def _sociavault_profile(self, username: str) -> dict:
        self._check_budget(0.001)
        resp = requests.get(
            f"{self._base_url}/profile",
            params={"username": username},
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        log_api_usage("sociavault", "profile", cost_usd=0.001)
        return resp.json().get("data", resp.json())

    # --- TwitterAPI.io methods ---

    def _twitterapi_io_search(self, query: str, count: int = 20) -> list[dict]:
        self._check_budget(0.01)
        resp = requests.get(
            f"{self._base_url}/tweet/advanced_search",
            params={"query": query, "queryType": "Latest"},
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        cost = count * 0.00015  # $0.15 per 1000 tweets
        log_api_usage("twitterapi_io", "search", cost_usd=cost)
        data = resp.json()
        return data.get("tweets", data.get("data", []))

    def _twitterapi_io_user_tweets(self, username: str, count: int = 20) -> list[dict]:
        self._check_budget(0.01)
        resp = requests.get(
            f"{self._base_url}/user/last_tweets",
            params={"userName": username},
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        cost = count * 0.00015
        log_api_usage("twitterapi_io", "user_tweets", cost_usd=cost)
        data = resp.json()
        return data.get("tweets", data.get("data", []))

    def _twitterapi_io_profile(self, username: str) -> dict:
        self._check_budget(0.001)
        resp = requests.get(
            f"{self._base_url}/user/profile",
            params={"userName": username},
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        log_api_usage("twitterapi_io", "profile", cost_usd=0.00018)
        return resp.json().get("data", resp.json())

    # --- Unified public interface ---

    def search_tweets(self, query: str, count: int = 20) -> list[dict]:
        """Search tweets by keyword."""
        if self.provider == "sociavault":
            return self._sociavault_search(query, count)
        return self._twitterapi_io_search(query, count)

    def get_user_tweets(self, username: str, count: int = 20) -> list[dict]:
        """Get recent tweets from a specific user."""
        if self.provider == "sociavault":
            return self._sociavault_user_tweets(username, count)
        return self._twitterapi_io_user_tweets(username, count)

    def get_user_profile(self, username: str) -> dict:
        """Get user profile information."""
        if self.provider == "sociavault":
            return self._sociavault_profile(username)
        return self._twitterapi_io_profile(username)

    def get_status(self) -> dict:
        """Get current API usage status."""
        monthly_cost = get_monthly_api_cost(self.provider)
        return {
            "provider": self.provider,
            "monthly_cost_usd": monthly_cost,
            "monthly_budget_usd": self.budget_limit,
            "remaining_budget_usd": self.budget_limit - monthly_cost,
        }
