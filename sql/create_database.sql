-- ===========================================================================
-- create_database.sql
-- Schema for air_india_youtube.db (SQLite).
--
-- In practice the tables are loaded by src/run_pipeline.py via
-- pandas.DataFrame.to_sql(); this DDL documents the equivalent schema for
-- anyone rebuilding the database by hand.
--
-- Dataset limitation (by design, not omission): the source video table has
-- NO like counts, comment counts, publish dates, or subscriber counts, so
-- those columns do not exist anywhere in this database.
-- ===========================================================================

DROP TABLE IF EXISTS videos;
DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS sentiment_results;

-- One row per YouTube video about the crash (93 videos, 42 channels).
CREATE TABLE videos (
    video_id            TEXT PRIMARY KEY,
    title               TEXT,
    duration_seconds    REAL,
    tags                TEXT,      -- semicolon-separated keyword list
    description         TEXT,
    allowratings        INTEGER,
    views               REAL,
    channel_name        TEXT,
    isprivate           INTEGER,
    -- engineered features
    title_length        INTEGER,
    title_word_count    INTEGER,
    description_length  INTEGER,
    tag_count           INTEGER,
    mentions_boeing     INTEGER,   -- descriptive indicator only
    mentions_survivor   INTEGER,
    mentions_investigation INTEGER,
    mentions_pilot      INTEGER,
    is_live_or_breaking INTEGER
);

-- One row per scraped comment. All comments in this dataset belong to a
-- single video (Firstpost, video_id 'bWO_1UwLh1I').
CREATE TABLE comments (
    comment_id            TEXT PRIMARY KEY,
    comment_text          TEXT,
    published_relative    TEXT,     -- raw label, e.g. '3 days ago (edited)'
    reply_level           INTEGER,
    comment_author        TEXT,
    video_id              TEXT REFERENCES videos(video_id),
    comment_likes         INTEGER,
    reply_count           INTEGER,
    approx_published_date TEXT,     -- derived; approximate to ~1 day
    approx_days_ago       REAL,
    is_edited             INTEGER,
    comment_length        INTEGER,
    comment_word_count    INTEGER,
    days_ago_bucket       INTEGER
);

-- VADER sentiment scores per comment.
CREATE TABLE sentiment_results (
    comment_id      TEXT PRIMARY KEY REFERENCES comments(comment_id),
    video_id        TEXT REFERENCES videos(video_id),
    comment_text    TEXT,
    comment_likes   INTEGER,
    days_ago_bucket INTEGER,
    vader_neg       REAL,
    vader_neu       REAL,
    vader_pos       REAL,
    vader_compound  REAL,           -- in [-1, 1]
    sentiment       TEXT            -- 'positive' | 'neutral' | 'negative'
);

CREATE INDEX IF NOT EXISTS idx_videos_channel   ON videos(channel_name);
CREATE INDEX IF NOT EXISTS idx_sent_sentiment   ON sentiment_results(sentiment);
CREATE INDEX IF NOT EXISTS idx_sent_day_bucket  ON sentiment_results(days_ago_bucket);
