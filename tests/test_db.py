"""Tests for database operations."""

import os
import tempfile

from hunter.db import (
    get_monthly_post_count,
    get_tweets_by_status,
    init_db,
    save_tweet,
    update_tweet_status,
)
from hunter.models.schemas import Tweet, TweetStatus


def test_init_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        # Should not raise
        init_db(db_path)  # idempotent
    finally:
        os.unlink(db_path)


def test_save_and_get_tweet():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        tweet = Tweet(content="Hello world #AI", status=TweetStatus.DRAFT, theme="test")
        tweet_id = save_tweet(tweet, db_path)
        assert tweet_id > 0

        drafts = get_tweets_by_status(TweetStatus.DRAFT, db_path)
        assert len(drafts) >= 1
        assert drafts[0].content == "Hello world #AI"
    finally:
        os.unlink(db_path)


def test_update_tweet_status():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        tweet = Tweet(content="Test tweet", status=TweetStatus.DRAFT)
        tweet_id = save_tweet(tweet, db_path)

        update_tweet_status(tweet_id, TweetStatus.APPROVED, db_path=db_path)
        approved = get_tweets_by_status(TweetStatus.APPROVED, db_path)
        assert len(approved) == 1
        assert approved[0].id == tweet_id
    finally:
        os.unlink(db_path)
