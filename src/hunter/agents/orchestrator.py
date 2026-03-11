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

    def run_planning(self, dry_run: bool = False) -> list[dict]:
        """Run the planning workflow: gather trends → create plan.

        Args:
            dry_run: If True, generate a template plan without calling the Claude API.

        Returns:
            List of content plan items
        """
        # Gather trends from reader API
        trends = []
        try:
            trends = self.reader.search_tweets("AI OR LLM OR ChatGPT", count=20)
        except Exception as e:
            print(f"[Warning] Could not fetch trends: {e}")

        if dry_run:
            plans = self._generate_template_plan()
        else:
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
            # Combine hook + description + why_viral for richer DB storage
            desc_parts = []
            if plan.get("hook"):
                desc_parts.append(f"[Hook] {plan['hook']}")
            desc_parts.append(plan.get("description", ""))
            if plan.get("why_viral"):
                desc_parts.append(f"[Viral] {plan['why_viral']}")
            full_desc = " | ".join(desc_parts)

            cp = ContentPlan(
                week_start=plan.get("day", ""),
                theme=plan.get("theme", ""),
                content_type=plan.get("content_type", "single"),
                description=full_desc,
                priority=plan.get("priority", 3),
            )
            plan["id"] = save_content_plan(cp)

        return plans

    def _generate_template_plan(self) -> list[dict]:
        """Generate a template-based weekly plan without API calls."""
        from datetime import datetime, timedelta

        today = datetime.now()
        templates = [
            {
                "theme": "本音・逆張り系",
                "content_type": "single",
                "hook": "ChatGPT最強って言ってる人、本当に他のLLM使ったことある？",
                "description": "主流意見への逆張りで議論を生む",
                "why_viral": "議論が起きて引用RTされる",
                "priority": 5,
            },
            {
                "theme": "触ってみた系",
                "content_type": "thread",
                "hook": "話題の〇〇を3日間ガチで使い倒した結論",
                "description": "実際に使った体験ベースのレビュー",
                "why_viral": "リアルな体験談は信頼される＆保存される",
                "priority": 4,
            },
            {
                "theme": "実践Tips",
                "content_type": "single",
                "hook": "ChatGPTが急にバカになった時の対処法",
                "description": "すぐ使える具体的なテクニック",
                "why_viral": "保存・ブクマされやすい",
                "priority": 4,
            },
            {
                "theme": "共感・あるある系",
                "content_type": "single",
                "hook": "AI使い始めた人が全員通る道",
                "description": "AIユーザーあるあるで共感を取る",
                "why_viral": "共感RTされやすい",
                "priority": 3,
            },
            {
                "theme": "比較・検証系",
                "content_type": "thread",
                "hook": "同じプロンプトでGPT-4, Claude, Geminiに聞いた結果",
                "description": "実際の比較結果を見せる",
                "why_viral": "みんな気になる比較は保存される",
                "priority": 4,
            },
            {
                "theme": "本音・逆張り系",
                "content_type": "single",
                "hook": "プログラミング学習にAI使うなって言う人いるけど",
                "description": "世間の常識に切り込む",
                "why_viral": "賛否両論で拡散する",
                "priority": 5,
            },
            {
                "theme": "速報・ニュース考察",
                "content_type": "single",
                "hook": "〇〇がリリースされたけど、冷静に見た方がいい",
                "description": "ニュース+自分の辛口見解",
                "why_viral": "独自視点でフォロー理由になる",
                "priority": 3,
            },
        ]

        plans = []
        for i, tmpl in enumerate(templates):
            day = today + timedelta(days=i)
            plan = {**tmpl, "day": day.strftime("%Y-%m-%d")}
            plans.append(plan)

        return plans

    def run_creation(self, plans: list[dict] | None = None, dry_run: bool = False) -> list[dict]:
        """Run the creation workflow: plan items → tweet drafts.

        Args:
            plans: Content plan items. If None, uses latest plans from DB.
            dry_run: If True, generate template tweets without calling the Claude API.

        Returns:
            List of created tweet drafts with IDs
        """
        if plans is None:
            from hunter.db import get_current_week_plans
            db_plans = get_current_week_plans()
            plans = []
            for p in db_plans:
                plan_dict = {"theme": p.theme, "content_type": p.content_type, "description": p.description}
                # Parse hook and why_viral from stored description
                if "[Hook]" in p.description:
                    parts = p.description.split(" | ")
                    for part in parts:
                        if part.startswith("[Hook] "):
                            plan_dict["hook"] = part[7:]
                        elif part.startswith("[Viral] "):
                            plan_dict["why_viral"] = part[8:]
                        else:
                            plan_dict["description"] = part
                plans.append(plan_dict)

        results = []
        for plan in plans:
            if dry_run:
                created = self._generate_template_tweet(plan)
            else:
                created = self.creator.create_tweet(
                    theme=plan.get("theme", ""),
                    description=plan.get("description", ""),
                    content_type=plan.get("content_type", "single"),
                    hook=plan.get("hook", ""),
                    why_viral=plan.get("why_viral", ""),
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

    def _generate_template_tweet(self, plan: dict) -> dict:
        """Generate a template tweet without API calls."""
        hook = plan.get("hook", "")
        description = plan.get("description", "")
        content_type = plan.get("content_type", "single")

        if content_type == "thread":
            return {
                "tweets": [
                    {"text": f"{hook}\n\n結論から言う👇", "type": "thread_part", "hashtags": []},
                    {"text": f"{description[:120]}\nこれがマジで重要。", "type": "thread_part", "hashtags": []},
                    {"text": "って話。気になったらフォローしとくと追加情報流す", "type": "thread_part", "hashtags": ["#AI"]},
                ],
                "alternatives": [],
            }
        else:
            return {
                "tweets": [
                    {"text": f"{hook}\n\n{description[:100]}", "type": "single", "hashtags": ["#AI"]},
                ],
                "alternatives": [],
            }

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
