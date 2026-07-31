"""
Phase 4 — VADER sentiment analysis of YouTube comments.

Methodology notes (also surfaced in the README and insights report):
  * VADER measures the *tone of language*, not factual accuracy, and does not
    reliably capture sarcasm, code-mixed Hindi/English ("Hinglish"), or
    culturally specific phrasing. Non-English text tends to score neutral.
  * On tragedy coverage, grief vocabulary ("lost", "tragic", crying emoji)
    scores negative even inside compassionate condolence messages, so a high
    negative share reflects sombre language — it is NOT evidence about the
    cause of the crash and must never be read that way.
"""

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Standard VADER thresholds for the compound score.
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05

_analyzer = SentimentIntensityAnalyzer()


def clean_comment_text(text):
    """Minimal cleaning for VADER: collapse whitespace, keep emoji.

    VADER scores punctuation emphasis, capitalization, and emoji, so the text
    is deliberately NOT lowercased or stripped of punctuation here.
    """
    if pd.isna(text):
        return ""
    return " ".join(str(text).split())


def score_comment(text):
    """Return VADER's neg/neu/pos/compound scores for one comment."""
    return _analyzer.polarity_scores(clean_comment_text(text))


def label_sentiment(compound):
    """Map a compound score to positive / neutral / negative."""
    if compound >= POSITIVE_THRESHOLD:
        return "positive"
    if compound <= NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"


def analyze_comments(comments, text_col="comment_text"):
    """Score every comment; returns a copy with vader_* and sentiment columns."""
    if text_col not in comments.columns:
        raise KeyError(f"comments table has no '{text_col}' column")
    out = comments.copy()
    scores = out[text_col].map(score_comment)
    out["vader_neg"] = [s["neg"] for s in scores]
    out["vader_neu"] = [s["neu"] for s in scores]
    out["vader_pos"] = [s["pos"] for s in scores]
    out["vader_compound"] = [s["compound"] for s in scores]
    out["sentiment"] = out["vader_compound"].map(label_sentiment)
    return out


def sentiment_summary(scored):
    """Counts, percentages, and mean compound per sentiment class."""
    counts = scored["sentiment"].value_counts()
    summary = pd.DataFrame({
        "count": counts,
        "percent": (counts / len(scored) * 100).round(1),
        "mean_compound": scored.groupby("sentiment")["vader_compound"]
                               .mean().round(3),
    })
    return summary.reindex(["positive", "neutral", "negative"]).reset_index()


def sentiment_by_day(scored):
    """Sentiment shares per approximate-days-ago bucket, oldest first."""
    if "days_ago_bucket" not in scored.columns:
        return None
    grouped = (scored.groupby("days_ago_bucket", observed=True)["sentiment"]
               .value_counts(normalize=True).unstack(fill_value=0) * 100)
    grouped["comments"] = scored.groupby("days_ago_bucket", observed=True).size()
    return grouped.round(1).sort_index(ascending=False).reset_index()


def most_liked_by_sentiment(scored, n=5, like_col="comment_likes"):
    """Top-n most-liked comments in each sentiment class."""
    if like_col not in scored.columns:
        return None
    frames = []
    for sentiment in ("positive", "neutral", "negative"):
        top = (scored[scored["sentiment"] == sentiment]
               .nlargest(n, like_col)
               [["sentiment", "comment_text", like_col, "vader_compound"]])
        frames.append(top)
    return pd.concat(frames, ignore_index=True)
