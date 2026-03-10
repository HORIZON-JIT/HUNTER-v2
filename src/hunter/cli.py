"""CLI interface for HUNTER-v2."""

import json

import click

from hunter.config import Settings
from hunter.db import (
    get_analytics_summary,
    get_tweets_by_status,
    init_db,
    save_analytics,
    update_tweet_status,
)
from hunter.models.schemas import Analytics, TweetStatus


@click.group()
@click.option("--config", default=None, help="Path to settings.yaml")
@click.pass_context
def cli(ctx, config):
    """HUNTER-v2: Twitter Growth Agent Team"""
    ctx.ensure_object(dict)
    ctx.obj["settings"] = Settings(config)
    init_db()


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status (posting limits, queue, API usage)."""
    from hunter.agents.orchestrator import Orchestrator

    settings = ctx.obj["settings"]
    orch = Orchestrator(settings)
    s = orch.get_status()

    click.echo("\n=== HUNTER-v2 Status ===\n")

    # Twitter posting status
    tw = s["twitter"]
    click.echo(f"Twitter (Free tier):")
    click.echo(f"  Posted this month: {tw['posted_this_month']} / {tw['monthly_limit']}")
    click.echo(f"  Remaining: {tw['remaining']}")

    # Reader API status
    rd = s["reader"]
    click.echo(f"\nReader API ({rd['provider']}):")
    click.echo(f"  Monthly cost: ${rd['monthly_cost_usd']:.2f} / ${rd['monthly_budget_usd']:.2f}")
    click.echo(f"  Remaining budget: ${rd['remaining_budget_usd']:.2f}")

    # Queue
    q = s["queue"]
    click.echo(f"\nQueue:")
    click.echo(f"  Drafts: {q['drafts']}")
    click.echo(f"  Approved: {q['approved']}")
    click.echo()


@cli.command()
@click.pass_context
def plan(ctx):
    """Generate a weekly content plan."""
    from hunter.agents.orchestrator import Orchestrator

    settings = ctx.obj["settings"]
    orch = Orchestrator(settings)

    click.echo("Generating weekly content plan...")
    plans = orch.run_planning()

    click.echo(f"\n=== Weekly Plan ({len(plans)} items) ===\n")
    for i, p in enumerate(plans, 1):
        click.echo(f"{i}. [{p.get('day', '?')}] {p.get('theme', '?')}")
        click.echo(f"   Type: {p.get('content_type', 'single')} | Priority: {p.get('priority', '?')}")
        click.echo(f"   {p.get('description', '')[:100]}")
        click.echo()

    click.echo(f"Plans saved to database.")


@cli.command()
@click.option("--count", default=5, help="Number of tweets to create")
@click.pass_context
def create(ctx, count):
    """Create tweet drafts from content plan."""
    from hunter.agents.orchestrator import Orchestrator

    settings = ctx.obj["settings"]
    orch = Orchestrator(settings)

    click.echo(f"Creating up to {count} tweet drafts...")
    results = orch.run_creation()

    if not results:
        click.echo("No plans found. Run 'hunter plan' first.")
        return

    results = results[:count]
    click.echo(f"\n=== Created {len(results)} Drafts ===\n")
    for r in results:
        click.echo(f"[#{r['id']}] ({r['theme']})")
        click.echo(f"  {r['content'][:200]}")
        click.echo()


@cli.command()
@click.pass_context
def review(ctx):
    """Review and approve/reject draft tweets."""
    drafts = get_tweets_by_status(TweetStatus.DRAFT)

    if not drafts:
        click.echo("No drafts to review.")
        return

    click.echo(f"\n=== {len(drafts)} Drafts to Review ===\n")
    for tweet in drafts:
        click.echo(f"--- Draft #{tweet.id} [{tweet.theme}] ---")
        click.echo(tweet.content)
        if tweet.thread_parts:
            click.echo(f"(Thread: {len(tweet.thread_parts)} parts)")
        click.echo()

        action = click.prompt(
            "Action", type=click.Choice(["approve", "reject", "skip", "quit"]), default="skip"
        )

        if action == "approve":
            update_tweet_status(tweet.id, TweetStatus.APPROVED)
            click.echo(f"  -> Approved #{tweet.id}")
        elif action == "reject":
            update_tweet_status(tweet.id, TweetStatus.REJECTED)
            click.echo(f"  -> Rejected #{tweet.id}")
        elif action == "quit":
            break
        click.echo()


@cli.command()
@click.option("--id", "tweet_ids", multiple=True, type=int, help="Specific tweet IDs to post")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def post(ctx, tweet_ids, yes):
    """Post approved tweets to Twitter."""
    from hunter.agents.orchestrator import Orchestrator

    settings = ctx.obj["settings"]

    if tweet_ids:
        tweets_to_post = list(tweet_ids)
    else:
        approved = get_tweets_by_status(TweetStatus.APPROVED)
        if not approved:
            click.echo("No approved tweets to post.")
            return
        tweets_to_post = [t.id for t in approved]

    click.echo(f"\nReady to post {len(tweets_to_post)} tweet(s).")

    if not yes:
        if not click.confirm("Proceed?"):
            click.echo("Cancelled.")
            return

    orch = Orchestrator(settings)
    results = orch.run_posting(tweets_to_post)

    for r in results:
        if r["status"] == "posted":
            click.echo(f"  Posted #{r['id']} -> twitter:{r['twitter_id']}")
        else:
            click.echo(f"  Failed #{r['id']}: {r.get('error', 'unknown')}")


@cli.command()
@click.option("--query", "-q", default="AI OR LLM", help="Search query")
@click.option("--count", "-n", default=10, help="Number of tweets")
@click.pass_context
def search(ctx, query, count):
    """Search tweets using reader API."""
    from hunter.reader_client import ReaderClient

    settings = ctx.obj["settings"]
    reader = ReaderClient(settings)

    click.echo(f"Searching: '{query}'...")
    try:
        tweets = reader.search_tweets(query, count)
        click.echo(f"\n=== {len(tweets)} Results ===\n")
        for t in tweets:
            text = t.get("text", t.get("content", ""))[:200]
            user = t.get("user", {}).get("screen_name", t.get("username", "?"))
            likes = t.get("likes", t.get("favorite_count", "?"))
            click.echo(f"@{user} ({likes} likes):")
            click.echo(f"  {text}")
            click.echo()
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.argument("username")
@click.option("--count", "-n", default=10, help="Number of tweets")
@click.pass_context
def spy(ctx, username, count):
    """View a user's recent tweets using reader API."""
    from hunter.reader_client import ReaderClient

    settings = ctx.obj["settings"]
    reader = ReaderClient(settings)

    click.echo(f"Fetching tweets from @{username}...")
    try:
        tweets = reader.get_user_tweets(username, count)
        click.echo(f"\n=== @{username}'s Recent Tweets ({len(tweets)}) ===\n")
        for t in tweets:
            text = t.get("text", t.get("content", ""))[:200]
            likes = t.get("likes", t.get("favorite_count", "?"))
            click.echo(f"({likes} likes) {text}")
            click.echo()
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.pass_context
def engage(ctx):
    """Get engagement suggestions from Community Manager agent."""
    from hunter.agents.orchestrator import Orchestrator
    from hunter.reader_client import ReaderClient

    settings = ctx.obj["settings"]
    reader = ReaderClient(settings)

    click.echo("Fetching trending AI tweets...")
    try:
        trends = reader.search_tweets("AI OR LLM OR ChatGPT", count=10)
    except Exception as e:
        click.echo(f"Could not fetch trends: {e}")
        return

    orch = Orchestrator(settings)
    click.echo("Generating engagement suggestions...")
    suggestions = orch.community.suggest_engagement(trends)

    click.echo("\n=== Engagement Suggestions ===\n")

    if suggestions.get("reply_suggestions"):
        click.echo("Reply ideas:")
        for r in suggestions["reply_suggestions"]:
            click.echo(f"  -> {r.get('target_tweet', '')[:80]}")
            click.echo(f"     Reply: {r.get('reply_text', '')}")
            click.echo()

    if suggestions.get("quote_rt_ideas"):
        click.echo("Quote RT ideas:")
        for q in suggestions["quote_rt_ideas"]:
            click.echo(f"  -> {q.get('original', '')[:80]}")
            click.echo(f"     Quote: {q.get('quote_text', '')}")
            click.echo()

    if suggestions.get("accounts_to_follow"):
        click.echo(f"Accounts to follow: {', '.join(suggestions['accounts_to_follow'])}")

    if suggestions.get("engagement_tips"):
        click.echo("\nTips:")
        for tip in suggestions["engagement_tips"]:
            click.echo(f"  - {tip}")


@cli.group()
def analytics():
    """Analytics commands."""
    pass


@analytics.command("add")
@click.option("--tweet-id", type=int, required=True, help="Tweet ID in DB")
@click.option("--likes", type=int, default=0)
@click.option("--retweets", type=int, default=0)
@click.option("--replies", type=int, default=0)
@click.option("--impressions", type=int, default=0)
def analytics_add(tweet_id, likes, retweets, replies, impressions):
    """Manually add analytics data for a tweet."""
    a = Analytics(
        tweet_id=tweet_id,
        likes=likes,
        retweets=retweets,
        replies=replies,
        impressions=impressions,
    )
    save_analytics(a)
    click.echo(f"Analytics saved for tweet #{tweet_id}")


@analytics.command("report")
@click.pass_context
def analytics_report(ctx):
    """Generate analytics report."""
    summary = get_analytics_summary()

    if not summary or summary.get("total_tweets", 0) == 0:
        click.echo("No analytics data yet. Use 'hunter analytics add' to add data.")
        return

    click.echo("\n=== Analytics Report ===\n")
    click.echo(f"Total tracked tweets: {summary['total_tweets']}")
    click.echo(f"Total likes: {summary['total_likes']}")
    click.echo(f"Total retweets: {summary['total_retweets']}")
    click.echo(f"Total replies: {summary['total_replies']}")
    click.echo(f"Total impressions: {summary['total_impressions']}")
    click.echo(f"Avg likes/tweet: {summary['avg_likes']:.1f}")
    click.echo(f"Avg retweets/tweet: {summary['avg_retweets']:.1f}")


if __name__ == "__main__":
    cli()
