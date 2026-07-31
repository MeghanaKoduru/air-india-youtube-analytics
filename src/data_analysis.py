"""
Phases 2–3 & 5 — Feature engineering, exploratory analysis, and text/keyword
analysis for the Air India Ahmedabad Crash YouTube dataset.

Every public function checks that its required columns exist and returns
``None`` (recording the reason via ``skipped``) when they do not, so the
pipeline degrades gracefully on schema changes.
"""

import re
from collections import Counter

import numpy as np
import pandas as pd

# Analyses that could not run because a source column is unavailable are
# appended here as (analysis, reason) and reported at the end of the run.
skipped = []


def _require(df, cols, analysis):
    """Return True when all ``cols`` exist in ``df``; else record the skip."""
    missing = [c for c in cols if c not in df.columns]
    if missing:
        skipped.append((analysis, f"missing column(s): {', '.join(missing)}"))
        return False
    return True


# --------------------------------------------------------------------------
# Phase 2 — feature engineering
# --------------------------------------------------------------------------

def add_video_features(videos):
    """Add engagement, time, and text features where source columns allow."""
    v = videos.copy()

    # Engagement metrics need likes/comment counts, which this dataset's
    # video table does not provide — guard each one independently.
    if _require(v, ["likes", "comment_count", "views"], "engagement_rate"):
        safe_views = v["views"].replace(0, np.nan)
        v["engagement_rate"] = (v["likes"] + v["comment_count"]) / safe_views * 100
    if _require(v, ["likes", "views"], "like_to_view_rate"):
        v["like_to_view_rate"] = v["likes"] / v["views"].replace(0, np.nan) * 100
    if _require(v, ["comment_count", "views"], "comment_to_view_rate"):
        v["comment_to_view_rate"] = (
            v["comment_count"] / v["views"].replace(0, np.nan) * 100)

    if "engagement_rate" in v.columns:
        # Percentile-based classification: bottom third / middle / top third.
        q1, q2 = v["engagement_rate"].quantile([1 / 3, 2 / 3])
        v["engagement_category"] = pd.cut(
            v["engagement_rate"], [-np.inf, q1, q2, np.inf],
            labels=["Low Engagement", "Medium Engagement", "High Engagement"])

    if _require(v, ["published_date"], "video time features"):
        d = v["published_date"]
        v["pub_year"] = d.dt.year
        v["pub_month"] = d.dt.month
        v["pub_day"] = d.dt.date
        v["pub_dayofweek"] = d.dt.day_name()
        v["pub_hour"] = d.dt.hour
        v["pub_week"] = d.dt.isocalendar().week
        v["days_since_first_video"] = (d - d.min()).dt.days

    if "title" in v.columns:
        v["title_length"] = v["title"].str.len()
        v["title_word_count"] = v["title"].str.split().str.len()
    if "description" in v.columns:
        v["description_length"] = v["description"].str.len()
    if "tags" in v.columns:
        v["tag_count"] = v["tags"].map(
            lambda t: len([k for k in str(t).split(";") if k.strip()]) if t else 0)

    # Descriptive keyword indicators (features only — never conclusions).
    theme_patterns = {
        "mentions_boeing": r"\bboeing|dreamliner|787\b",
        "mentions_survivor": r"\bsurviv",
        "mentions_investigation": r"\binvestigat|black ?box|probe\b",
        "mentions_pilot": r"\bpilot|captain\b",
        "is_live_or_breaking": r"\blive\b|\bbreaking\b",
    }
    if "title" in v.columns:
        for feat, pattern in theme_patterns.items():
            v[feat] = v["title"].str.contains(pattern, case=False, regex=True)
    return v


def add_comment_features(comments):
    """Add per-comment length and (approximate) time-bucket features."""
    c = comments.copy()
    if "comment_text" in c.columns:
        c["comment_length"] = c["comment_text"].str.len()
        c["comment_word_count"] = c["comment_text"].str.split().str.len()
    if "approx_days_ago" in c.columns:
        # Whole-day buckets: 0 = the scrape day.
        c["days_ago_bucket"] = np.floor(c["approx_days_ago"]).astype("Int64")
    return c


# --------------------------------------------------------------------------
# Phase 3 — exploratory analysis
# --------------------------------------------------------------------------

def dataset_overview(videos, comments):
    """Headline KPI dictionary; unavailable metrics are reported as such."""
    kpi = {
        "total_videos": len(videos),
        "unique_channels": videos["channel_name"].nunique()
        if "channel_name" in videos.columns else None,
        "total_comments_scraped": len(comments),
        "videos_with_scraped_comments": comments["video_id"].nunique()
        if "video_id" in comments.columns else None,
    }
    if "views" in videos.columns:
        kpi["total_views"] = int(videos["views"].sum())
        kpi["average_views_per_video"] = round(float(videos["views"].mean()), 1)
        kpi["median_views_per_video"] = float(videos["views"].median())
    for metric in ("likes", "comment_count", "engagement_rate"):
        if metric in videos.columns:
            kpi[f"total_{metric}"] = float(videos[metric].sum())
        else:
            kpi[f"total_{metric}"] = "not available in dataset"
    if "published_date" in videos.columns:
        kpi["date_range"] = (
            f"{videos['published_date'].min()} to {videos['published_date'].max()}")
    else:
        kpi["date_range"] = "not available (video table has no publish dates)"
        skipped.append(("dataset date range", "no published_date column"))
    return kpi


def top_videos(videos, by="views", n=10, min_views=None):
    """Top-n videos by a metric; optional minimum-view threshold."""
    if not _require(videos, [by, "title"], f"top videos by {by}"):
        return None
    v = videos
    if min_views is not None and "views" in v.columns:
        v = v[v["views"] >= min_views]
    cols = [c for c in ("title", "channel_name", "views", "likes",
                        "comment_count", "engagement_rate", by) if c in v.columns]
    return (v.sort_values(by, ascending=False)
             .head(n)[list(dict.fromkeys(cols))]
             .reset_index(drop=True))


def channel_performance(videos):
    """Per-channel aggregates for every metric the dataset provides."""
    if not _require(videos, ["channel_name", "views"], "channel performance"):
        return None
    agg = {"views": ["sum", "mean"], "video_id": "count"}
    for extra in ("likes", "comment_count", "engagement_rate"):
        if extra in videos.columns:
            agg[extra] = "sum" if extra != "engagement_rate" else "mean"
    perf = videos.groupby("channel_name").agg(agg)
    perf.columns = ["_".join(c).strip("_") for c in perf.columns]
    perf = perf.rename(columns={
        "views_sum": "total_views", "views_mean": "avg_views",
        "video_id_count": "video_count"})
    return perf.sort_values("total_views", ascending=False).reset_index()


def correlation_matrix(videos):
    """Correlation across whichever numeric metrics exist (>= 2 required)."""
    candidates = ["views", "likes", "comment_count", "engagement_rate",
                  "duration_seconds", "title_length", "description_length",
                  "tag_count"]
    present = [c for c in candidates if c in videos.columns]
    if len(present) < 2:
        skipped.append(("correlation analysis", "fewer than 2 numeric metrics"))
        return None
    return videos[present].corr(numeric_only=True)


def comment_volume_by_day(comments):
    """Comment counts per approximate-days-ago bucket (oldest first)."""
    if not _require(comments, ["days_ago_bucket"], "comment volume by day"):
        return None
    out = (comments.groupby("days_ago_bucket", observed=True)
           .size().rename("comments").reset_index()
           .sort_values("days_ago_bucket", ascending=False))
    return out


# --------------------------------------------------------------------------
# Phase 5 — text & keyword analysis
# --------------------------------------------------------------------------

STOP_WORDS = set("""
a about above after again against all am an and any are as at be because been
before being below between both but by can did do does doing down during each
few for from further had has have having he her here hers herself him himself
his how i if in into is it its itself just me more most my myself no nor not
now of off on once only or other our ours ourselves out over own same she
should so some such than that the their theirs them themselves then there
these they this those through to too under until up very was we were what when
where which while who whom why will with you your yours yourself yourselves
im ive dont didnt cant wont isnt arent wasnt werent its lets thats hes shes
theyre youre weve theyve also would could get got even much many still really
one two like say said see u r us
""".split())


def tokenize(text, min_len=3):
    """Lowercase word tokens with URLs, stop words, and short words removed."""
    text = re.sub(r"https?://\S+|www\.\S+", " ", str(text).lower())
    words = re.findall(r"[a-z][a-z']+", text)
    return [w.strip("'") for w in words
            if len(w) >= min_len and w not in STOP_WORDS]


def top_terms(series, n=20, ngram=1):
    """Top-n terms or bigrams across a text column."""
    counter = Counter()
    for text in series.dropna():
        tokens = tokenize(text)
        if ngram == 1:
            counter.update(tokens)
        else:
            counter.update(
                " ".join(tokens[i:i + ngram])
                for i in range(len(tokens) - ngram + 1))
    label = "keyword" if ngram == 1 else "bigram"
    return pd.DataFrame(counter.most_common(n), columns=[label, "count"])
