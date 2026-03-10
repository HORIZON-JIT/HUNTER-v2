"""Orchestrator Agent - coordinates all agents and manages workflow."""

from hunter.agents.strategist import StrategistAgent
from hunter.agents.creator import CreatorAgent
from hunter.agents.analyst import AnalystAgent
from hunter.agents.community import CommunityAgent
from hunter.config import Settings
from hunter.db import (
    get_tweets_by_status,
    save_content_plan,
    save_tweet,
    update_tweet_status,
)
from hunter.models.schemas import ContentPlan, Tweet, TweetStatus
from hunter.reader_client import ReaderClient
from hunter.twitter_client import TwitterClient


class Orchestrator:
    """Central coordinator for all agents."""

    def __init__(self, settings: Settings):
        self.settings = settings
        api_key = settings.anthropic_api_key
        model = settings.agent_model

        # Initialize agents
        self.strategist = StrategistAgent(api_key, model)
        self.creator = CreatorAgent(api_key, model)
        self.analyst = AnalystAgent(api_key, model)
        self.community = CommunityAgent(api_key, model)

        # Initialize clients
        self.twitter = TwitterClient(settings)
        self.reader = ReaderClient(settings)

    def run_planning(self) -> list[dict]:
        """Run the planning workflow: gather trends → create plan.

        Returns:
            List of content plan items
        """
        # Gather trends from reader API
        trends = []
        try:
            trends = self.reader.search_tweets("AI OR LLM OR ChatGPT", count=20)
        except Exception as e:
            print(f"[Warning] Could not fetch trends: {e}")

        # Get past tweets for context
        past = get_tweets_by_status(TweetStatus.POSTED)

        # Create weekly plan
        plans = self.strategist.create_weekly_plan(
            trends=trends,
            past_tweets=[{"content": t.content} for t in past[:5]],
            config=self.settings.content,
        )

        # Save plans to DB
        for plan in plans:
            cp = ContentPlan(
                week_start=plan.get("day", ""),
                theme=plan.get("theme", ""),
                content_type=plan.get("content_type", "single"),
                description=plan.get("description", ""),
                priority=plan.get("priority", 3),
            )
            plan["id"] = save_content_plan(cp)

        return plans

    def run_creation(self, plans: list[dict] | None = None) -> list[dict]:
        """Run the creation workflow: plan items → tweet drafts.

        Args:
            plans: Content plan items. If None, uses latest plans from DB.

        Returns:
            List of created tweet drafts with IDs
        """
        if plans is None:
            from hunter.db import get_current_week_plans
            db_plans = get_current_week_plans()
            plans = [
                {"theme": p.theme, "content_type": p.content_type, "description": p.description}
                for p in db_plans
            ]

        results = []
        for plan in plans:
            created = self.creator.create_tweet(
                theme=plan.get("theme", ""),
                description=plan.get("description", ""),
                content_type=plan.get("content_type", "single"),
            )

            # Save main tweet
            for tweet_data in created.get("tweets", []):
                tweet = Tweet(
                    content=tweet_data.get("text", ""),
                    content_type=plan.get("content_type", "single"),
                    thread_parts=([t["text"] for t in created["tweets"]] if plan.get("content_type") == "thread" else []),
                    status=TweetStatus.DRAFT,
                    theme=plan.get("theme", ""),
                )
                tweet_id = save_tweet(tweet)
                results.append({
                    "id": tweet_id,
                    "content": tweet.content,
                    "theme": tweet.theme,
                    "type": tweet.content_type,
                })
                # Only save first tweet for single type
                if plan.get("content_type") != "thread":
                    break

        return results

    def run_posting(self, tweet_ids: list[int] | None = None) -> list[dict]:
        """Post approved tweets.

        Args:
            tweet_ids: Specific tweet IDs to post. If None, posts all approved.

        Returns:
            List of posted tweet results
        """
        if tweet_ids:
            from hunter.db import get_connection
            conn = get_connection()
            tweets = []
            for tid in tweet_ids:
                row = conn.execute("SELECT * FROM tweets WHERE id = ? AND status = 'approved'", (tid,)).fetchone()
                if row:
                    from hunter.db import _row_to_tweet
                    tweets.append(_row_to_tweet(row))
            conn.close()
        else:
            tweets = get_tweets_by_status(TweetStatus.APPROVED)

        results = []
        for tweet in tweets:
            try:
                if tweet.content_type == "thread" and tweet.thread_parts:
                    posted = self.twitter.post_thread(tweet.thread_parts)
                    twitter_id = posted[0]["id"]
                else:
                    posted = self.twitter.post_tweet(tweet.content)
                    twitter_id = posted["id"]

                update_tweet_status(tweet.id, TweetStatus.POSTED, twitter_id)
                results.append({"id": tweet.id, "twitter_id": twitter_id, "status": "posted"})
            except Exception as e:
                update_tweet_status(tweet.id, TweetStatus.FAILED)
                results.append({"id": tweet.id, "status": "failed", "error": str(e)})

        return results

    def get_status(self) -> dict:
        """Get overall system status."""
        twitter_status = self.twitter.get_status()
        reader_status = self.reader.get_status()
        drafts = get_tweets_by_status(TweetStatus.DRAFT)
        approved = get_tweets_by_status(TweetStatus.APPROVED)

        return {
            "twitter": twitter_status,
            "reader": reader_status,
            "queue": {
                "drafts": len(drafts),
                "approved": len(approved),
            },
        }
