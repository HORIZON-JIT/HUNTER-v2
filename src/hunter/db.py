"""SQLite database operations for HUNTER-v2."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from hunter.models.schemas import Analytics, ApiUsage, ContentPlan, Tweet


DB_PATH = Path(__file__).parent.parent.parent / "hunter.db"


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a database connection."""
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str | None = None) -> None:
    """Initialize database tables."""
    conn = get_connection(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tweets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'single',
                thread_parts TEXT DEFAULT '[]',
                status TEXT DEFAULT 'draft',
                theme TEXT DEFAULT '',
                scheduled_at TEXT,
                posted_at TEXT,
                twitter_id TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS content_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                theme TEXT NOT NULL,
                content_type TEXT DEFAULT 'single',
                description TEXT DEFAULT '',
                priority INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id INTEGER,
                twitter_id TEXT,
                likes INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                recorded_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (tweet_id) REFERENCES tweets(id)
            );

            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                endpoint TEXT DEFAULT '',
                cost_usd REAL DEFAULT 0.0,
                recorded_at TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
    finally:
        conn.close()


# --- Tweet operations ---

def save_tweet(tweet: Tweet, db_path: str | None = None) -> int:
    """Save a tweet and return its ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO tweets (content, content_type, thread_parts, status, theme, scheduled_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                tweet.content,
                tweet.content_type,
                json.dumps(tweet.thread_parts),
                tweet.status,
                tweet.theme,
                tweet.scheduled_at.isoformat() if tweet.scheduled_at else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_tweet_status(tweet_id: int, status: str, twitter_id: str | None = None, db_path: str | None = None) -> None:
    """Update tweet status."""
    conn = get_connection(db_path)
    try:
        if status == "posted":
            conn.execute(
                "UPDATE tweets SET status = ?, twitter_id = ?, posted_at = ? WHERE id = ?",
                (status, twitter_id, datetime.now().isoformat(), tweet_id),
            )
        else:
            conn.execute("UPDATE tweets SET status = ? WHERE id = ?", (status, tweet_id))
        conn.commit()
    finally:
        conn.close()


def get_tweets_by_status(status: str, db_path: str | None = None) -> list[Tweet]:
    """Get tweets by status."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM tweets WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        return [_row_to_tweet(row) for row in rows]
    finally:
        conn.close()


def get_monthly_post_count(db_path: str | None = None) -> int:
    """Get number of tweets posted this month."""
    conn = get_connection(db_path)
    try:
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0).isoformat()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM tweets WHERE status = 'posted' AND posted_at >= ?",
            (month_start,),
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


# --- Content Plan operations ---

def save_content_plan(plan: ContentPlan, db_path: str | None = None) -> int:
    """Save a content plan and return its ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO content_plans (week_start, theme, content_type, description, priority)
               VALUES (?, ?, ?, ?, ?)""",
            (plan.week_start, plan.theme, plan.content_type, plan.description, plan.priority),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_current_week_plans(db_path: str | None = None) -> list[ContentPlan]:
    """Get content plans for the current week."""
    conn = get_connection(db_path)
    try:
        now = datetime.now()
        week_start = now.strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT * FROM content_plans WHERE week_start >= ? ORDER BY priority DESC",
            (week_start,),
        ).fetchall()
        return [_row_to_plan(row) for row in rows]
    finally:
        conn.close()


# --- Analytics operations ---

def save_analytics(analytics: Analytics, db_path: str | None = None) -> int:
    """Save analytics data."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO analytics (tweet_id, twitter_id, likes, retweets, replies, impressions)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (analytics.tweet_id, analytics.twitter_id, analytics.likes, analytics.retweets, analytics.replies, analytics.impressions),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_analytics_summary(db_path: str | None = None) -> dict:
    """Get summary analytics."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_tweets,
                COALESCE(SUM(likes), 0) as total_likes,
                COALESCE(SUM(retweets), 0) as total_retweets,
                COALESCE(SUM(replies), 0) as total_replies,
                COALESCE(SUM(impressions), 0) as total_impressions,
                COALESCE(AVG(likes), 0) as avg_likes,
                COALESCE(AVG(retweets), 0) as avg_retweets
            FROM analytics
        """).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


# --- API Usage operations ---

def log_api_usage(provider: str, endpoint: str, cost_usd: float = 0.0, db_path: str | None = None) -> None:
    """Log an API call for cost tracking."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO api_usage (provider, endpoint, cost_usd) VALUES (?, ?, ?)",
            (provider, endpoint, cost_usd),
        )
        conn.commit()
    finally:
        conn.close()


def get_monthly_api_cost(provider: str | None = None, db_path: str | None = None) -> float:
    """Get total API cost for the current month."""
    conn = get_connection(db_path)
    try:
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0).isoformat()
        if provider:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) as total FROM api_usage WHERE provider = ? AND recorded_at >= ?",
                (provider, month_start),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) as total FROM api_usage WHERE recorded_at >= ?",
                (month_start,),
            ).fetchone()
        return row["total"] if row else 0.0
    finally:
        conn.close()


# --- Helper functions ---

def _row_to_tweet(row: sqlite3.Row) -> Tweet:
    return Tweet(
        id=row["id"],
        content=row["content"],
        content_type=row["content_type"],
        thread_parts=json.loads(row["thread_parts"]) if row["thread_parts"] else [],
        status=row["status"],
        theme=row["theme"],
        scheduled_at=datetime.fromisoformat(row["scheduled_at"]) if row["scheduled_at"] else None,
        posted_at=datetime.fromisoformat(row["posted_at"]) if row["posted_at"] else None,
        twitter_id=row["twitter_id"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
    )


def _row_to_plan(row: sqlite3.Row) -> ContentPlan:
    return ContentPlan(
        id=row["id"],
        week_start=row["week_start"],
        theme=row["theme"],
        content_type=row["content_type"],
        description=row["description"],
        priority=row["priority"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
    )
