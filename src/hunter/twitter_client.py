"""Twitter Official API client for posting tweets (Free tier)."""

import tweepy

from hunter.config import Settings
from hunter.db import get_monthly_post_count, log_api_usage


FREE_TIER_MONTHLY_LIMIT = 1500


class TwitterClient:
    """Twitter API v2 client for posting only (Free tier)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None

    @property
    def client(self) -> tweepy.Client:
        if self._client is None:
            env = self.settings.env
            self._client = tweepy.Client(
                bearer_token=env["twitter_bearer_token"],
                consumer_key=env["twitter_api_key"],
                consumer_secret=env["twitter_api_secret"],
                access_token=env["twitter_access_token"],
                access_token_secret=env["twitter_access_token_secret"],
            )
        return self._client

    def check_limit(self) -> tuple[bool, int]:
        """Check if we're within the monthly posting limit.

        Returns:
            (can_post, remaining_count)
        """
        max_monthly = self.settings.posting.get("max_monthly_tweets", 1400)
        posted = get_monthly_post_count()
        remaining = max_monthly - posted
        return remaining > 0, remaining

    def post_tweet(self, text: str) -> dict:
        """Post a single tweet.

        Returns:
            {"id": "tweet_id", "text": "posted text"}
        """
        can_post, remaining = self.check_limit()
        if not can_post:
            raise RuntimeError(f"Monthly posting limit reached. Remaining: {remaining}")

        if len(text) > 280:
            raise ValueError(f"Tweet too long: {len(text)} chars (max 280)")

        response = self.client.create_tweet(text=text)
        tweet_id = str(response.data["id"])

        log_api_usage("twitter_official", "create_tweet", cost_usd=0.0)

        return {"id": tweet_id, "text": text}

    def post_thread(self, texts: list[str]) -> list[dict]:
        """Post a thread (multiple tweets connected by replies).

        Returns:
            List of {"id": "tweet_id", "text": "posted text"}
        """
        can_post, remaining = self.check_limit()
        if remaining < len(texts):
            raise RuntimeError(f"Not enough remaining posts. Need {len(texts)}, have {remaining}")

        max_length = self.settings.posting.get("thread_max_length", 10)
        if len(texts) > max_length:
            raise ValueError(f"Thread too long: {len(texts)} parts (max {max_length})")

        results = []
        reply_to_id = None

        for text in texts:
            if len(text) > 280:
                raise ValueError(f"Tweet in thread too long: {len(text)} chars (max 280)")

            if reply_to_id:
                response = self.client.create_tweet(text=text, in_reply_to_tweet_id=reply_to_id)
            else:
                response = self.client.create_tweet(text=text)

            tweet_id = str(response.data["id"])
            reply_to_id = tweet_id
            results.append({"id": tweet_id, "text": text})

            log_api_usage("twitter_official", "create_tweet", cost_usd=0.0)

        return results

    def get_status(self) -> dict:
        """Get current posting status."""
        posted = get_monthly_post_count()
        max_monthly = self.settings.posting.get("max_monthly_tweets", 1400)
        return {
            "posted_this_month": posted,
            "monthly_limit": max_monthly,
            "remaining": max_monthly - posted,
            "free_tier_limit": FREE_TIER_MONTHLY_LIMIT,
        }
