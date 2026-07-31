-- ===========================================================================
-- business_analysis.sql — SQLite queries against air_india_youtube.db
--
-- Numbering follows the project brief. Queries whose source columns do not
-- exist in this dataset (likes, video comment counts, publish dates) are
-- kept in place with an explicit SKIPPED note and, where possible, the
-- closest supported substitute — so the limitation is documented in the
-- deliverable itself rather than silently dropped.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- Q1. Business question: which individual videos drew the largest audiences?
-- ---------------------------------------------------------------------------
SELECT title, channel_name, CAST(views AS INTEGER) AS views,
       RANK() OVER (ORDER BY views DESC) AS view_rank
FROM videos
ORDER BY views DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- Q2. Top 10 videos by engagement rate.
-- SKIPPED: engagement rate needs like/comment counts, which the video table
-- does not contain. Substitute: views normalized per minute of runtime, a
-- rough proxy for how efficiently a video converted airtime into audience.
-- ---------------------------------------------------------------------------
SELECT title, channel_name, CAST(views AS INTEGER) AS views,
       ROUND(duration_seconds / 60.0, 1) AS minutes,
       ROUND(views / NULLIF(duration_seconds / 60.0, 0), 0) AS views_per_minute
FROM videos
WHERE duration_seconds >= 60          -- exclude Shorts-length clips
ORDER BY views_per_minute DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- Q3. Business question: which channels captured the most total viewership?
-- ---------------------------------------------------------------------------
SELECT channel_name,
       COUNT(*)                    AS video_count,
       CAST(SUM(views) AS INTEGER) AS total_views,
       RANK() OVER (ORDER BY SUM(views) DESC) AS channel_rank
FROM videos
GROUP BY channel_name
ORDER BY total_views DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- Q4. Business question: how many views does a typical video earn, per channel?
-- ---------------------------------------------------------------------------
SELECT channel_name,
       COUNT(*)                        AS video_count,
       CAST(AVG(views) AS INTEGER)     AS avg_views,
       CAST(MAX(views) AS INTEGER)     AS best_video_views
FROM videos
GROUP BY channel_name
ORDER BY avg_views DESC;

-- ---------------------------------------------------------------------------
-- Q5. Total engagement by channel.
-- SKIPPED for video-level likes/comments (not in dataset). Substitute: for
-- the one video with scraped comments, total comment engagement by channel.
-- ---------------------------------------------------------------------------
SELECT v.channel_name,
       COUNT(s.comment_id)     AS comments_scraped,
       SUM(s.comment_likes)    AS total_comment_likes
FROM sentiment_results s
JOIN videos v USING (video_id)
GROUP BY v.channel_name;

-- ---------------------------------------------------------------------------
-- Q6. Business question: how concentrated is coverage — videos per channel?
-- ---------------------------------------------------------------------------
SELECT channel_name, COUNT(*) AS video_count,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM videos), 1) AS pct_of_all_videos
FROM videos
GROUP BY channel_name
ORDER BY video_count DESC;

-- ---------------------------------------------------------------------------
-- Q7. Videos published by date.
-- SKIPPED: the video table has no publish dates. Substitute: comment volume
-- by approximate day (derived from relative labels; scrape day = bucket 0).
-- ---------------------------------------------------------------------------
SELECT days_ago_bucket   AS approx_days_before_scrape,
       COUNT(*)          AS comments
FROM sentiment_results
GROUP BY days_ago_bucket
ORDER BY days_ago_bucket DESC;

-- ---------------------------------------------------------------------------
-- Q8. Average engagement rate by month.
-- SKIPPED entirely: requires both engagement metrics and publish dates,
-- neither of which exists in this dataset.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- Q9. Most-commented videos.
-- Note: comments were scraped for a single video, so this returns one row —
-- kept as evidence of that limitation.
-- ---------------------------------------------------------------------------
SELECT v.title, v.channel_name, COUNT(*) AS comments_scraped
FROM sentiment_results s
JOIN videos v USING (video_id)
GROUP BY v.video_id
ORDER BY comments_scraped DESC;

-- ---------------------------------------------------------------------------
-- Q10. Business question: what is the overall tone of audience comments?
-- ---------------------------------------------------------------------------
SELECT sentiment,
       COUNT(*) AS comments,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct,
       ROUND(AVG(vader_compound), 3) AS avg_compound
FROM sentiment_results
GROUP BY sentiment
ORDER BY comments DESC;

-- ---------------------------------------------------------------------------
-- Q11. Average sentiment by channel (for channels with scraped comments).
-- ---------------------------------------------------------------------------
SELECT v.channel_name,
       COUNT(*) AS comments,
       ROUND(AVG(s.vader_compound), 3) AS avg_compound,
       CASE
           WHEN AVG(s.vader_compound) >= 0.05  THEN 'positive tone'
           WHEN AVG(s.vader_compound) <= -0.05 THEN 'negative / sombre tone'
           ELSE 'neutral tone'
       END AS tone
FROM sentiment_results s
JOIN videos v USING (video_id)
GROUP BY v.channel_name;

-- ---------------------------------------------------------------------------
-- Q12. Channels with the highest engagement.
-- SKIPPED for video engagement (no likes). Substitute: which sentiment class
-- earns the most likes per comment — do sombre or hopeful comments resonate?
-- ---------------------------------------------------------------------------
SELECT sentiment,
       COUNT(*)                          AS comments,
       SUM(comment_likes)                AS total_likes,
       ROUND(AVG(comment_likes), 2)      AS avg_likes_per_comment
FROM sentiment_results
GROUP BY sentiment
ORDER BY avg_likes_per_comment DESC;

-- ---------------------------------------------------------------------------
-- Q13. Business question: which videos out-performed the dataset average?
-- ---------------------------------------------------------------------------
WITH stats AS (
    SELECT AVG(views) AS avg_views FROM videos
)
SELECT v.title, v.channel_name,
       CAST(v.views AS INTEGER)  AS views,
       CAST(s.avg_views AS INTEGER) AS dataset_avg_views,
       ROUND(v.views / s.avg_views, 1) AS times_above_average
FROM videos v
CROSS JOIN stats s
WHERE v.views > s.avg_views
ORDER BY v.views DESC;

-- ---------------------------------------------------------------------------
-- Q14. Videos with above-average engagement.
-- SKIPPED for engagement rate (no likes/comment counts). Substitute:
-- comments whose like count is above the average — the audience-validated
-- voices in the thread — bucketed by sentiment.
-- ---------------------------------------------------------------------------
WITH stats AS (
    SELECT AVG(comment_likes) AS avg_likes FROM sentiment_results
)
SELECT s.sentiment,
       COUNT(*) AS above_average_comments,
       ROUND(AVG(s.vader_compound), 3) AS avg_compound
FROM sentiment_results s
CROSS JOIN stats st
WHERE s.comment_likes > st.avg_likes
GROUP BY s.sentiment
ORDER BY above_average_comments DESC;

-- ---------------------------------------------------------------------------
-- Q15. Monthly performance trends.
-- SKIPPED: no publish dates exist. Substitute: day-over-day sentiment trend
-- with a window-function share calculation and a CASE tone label per day.
-- ---------------------------------------------------------------------------
WITH daily AS (
    SELECT days_ago_bucket,
           COUNT(*)                                            AS comments,
           SUM(CASE WHEN sentiment = 'negative' THEN 1 END)    AS negative,
           SUM(CASE WHEN sentiment = 'positive' THEN 1 END)    AS positive,
           ROUND(AVG(vader_compound), 3)                       AS avg_compound
    FROM sentiment_results
    GROUP BY days_ago_bucket
)
SELECT days_ago_bucket AS approx_days_before_scrape,
       comments,
       ROUND(100.0 * negative / comments, 1) AS pct_negative,
       ROUND(100.0 * positive / comments, 1) AS pct_positive,
       avg_compound,
       comments - LAG(comments) OVER (ORDER BY days_ago_bucket DESC)
           AS volume_change_vs_prev_day
FROM daily
ORDER BY days_ago_bucket DESC;
