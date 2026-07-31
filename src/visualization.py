"""
Phase 6 — chart generation.

Every function takes prepared data, draws one chart, and saves a high-res PNG
into outputs/charts/. Functions return the output path, or None when the
required data was unavailable (the caller records the skip).

Style: quiet grid, thin marks, horizontal bars for long labels, K/M-formatted
values, direct labels only where they help. Sentiment always uses the same
fixed color mapping so the classes are consistent across charts.
"""

import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless rendering
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

ACCENT = "#2a78d6"       # primary series hue
ACCENT_2 = "#eb6834"     # secondary hue
SENTIMENT_COLORS = {     # fixed: color follows the class, never the rank
    "positive": "#2a78d6",
    "neutral": "#a8a69e",
    "negative": "#e34948",
}
INK = "#0b0b0b"
MUTED = "#898781"

sns.set_theme(style="whitegrid", rc={
    "axes.edgecolor": "#c3c2b7",
    "grid.color": "#e1e0d9",
    "grid.linewidth": 0.8,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "font.family": "sans-serif",
})


def _fmt_compact(value, _pos=None):
    """1,200,000 -> 1.2M ; 25,000 -> 25K (axis/label formatter)."""
    if abs(value) >= 1e6:
        return f"{value / 1e6:.1f}M".replace(".0M", "M")
    if abs(value) >= 1e3:
        return f"{value / 1e3:.0f}K"
    return f"{value:.0f}"


def _save(fig, charts_dir, name):
    charts_dir = Path(charts_dir)
    charts_dir.mkdir(parents=True, exist_ok=True)
    path = charts_dir / name
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _wrap(labels, width=48):
    return ["\n".join(textwrap.wrap(str(l), width)) for l in labels]


def top_videos_by_views(videos, charts_dir, n=10):
    if "views" not in videos.columns or "title" not in videos.columns:
        return None
    data = videos.nlargest(n, "views")
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(_wrap(data["title"]), data["views"], color=ACCENT, height=0.62)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_compact))
    ax.bar_label(bars, labels=[_fmt_compact(v) for v in data["views"]],
                 padding=4, fontsize=9, color=INK)
    ax.set_title(f"Top {n} videos by views")
    ax.set_xlabel("Views")
    ax.tick_params(axis="y", labelsize=8.5)
    sns.despine(left=True)
    return _save(fig, charts_dir, "01_top10_videos_by_views.png")


def top_channels_by_views(channel_perf, charts_dir, n=10):
    if channel_perf is None:
        return None
    data = channel_perf.nlargest(n, "total_views")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.barh(data["channel_name"], data["total_views"],
                   color=ACCENT, height=0.62)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_compact))
    ax.bar_label(bars, labels=[_fmt_compact(v) for v in data["total_views"]],
                 padding=4, fontsize=9, color=INK)
    ax.set_title(f"Top {n} channels by total views")
    ax.set_xlabel("Total views across the channel's videos in the dataset")
    sns.despine(left=True)
    return _save(fig, charts_dir, "02_top10_channels_by_total_views.png")


def channel_avg_views(channel_perf, charts_dir, n=10, min_videos=2):
    """Average views per video by channel (substitute for the engagement-rate
    ranking, which needs like/comment counts the dataset does not provide).
    Channels with fewer than ``min_videos`` are excluded so one lucky upload
    does not dominate."""
    if channel_perf is None:
        return None
    eligible = channel_perf[channel_perf["video_count"] >= min_videos]
    if eligible.empty:
        return None
    data = eligible.nlargest(n, "avg_views")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.barh(data["channel_name"], data["avg_views"],
                   color=ACCENT_2, height=0.62)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_compact))
    ax.bar_label(bars, labels=[_fmt_compact(v) for v in data["avg_views"]],
                 padding=4, fontsize=9, color=INK)
    ax.set_title(f"Average views per video — channels with ≥{min_videos} videos")
    ax.set_xlabel("Average views per video")
    sns.despine(left=True)
    return _save(fig, charts_dir, "03_channel_avg_views.png")


def view_distribution(videos, charts_dir):
    if "views" not in videos.columns:
        return None
    views = videos["views"].dropna()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    axes[0].hist(np.log10(views.clip(lower=1)), bins=24,
                 color=ACCENT, edgecolor="white")
    axes[0].set_title("View distribution (log10 scale)")
    axes[0].set_xlabel("log10(views)")
    axes[0].set_ylabel("Videos")
    sns.boxplot(x=views, ax=axes[1], color=ACCENT, width=0.35,
                fliersize=3, linewidth=1)
    axes[1].set_xscale("log")
    axes[1].xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_compact))
    axes[1].set_title("View distribution (log axis)")
    axes[1].set_xlabel("Views")
    fig.tight_layout()
    return _save(fig, charts_dir, "04_view_distribution.png")


def duration_distribution(videos, charts_dir):
    if "duration_seconds" not in videos.columns:
        return None
    minutes = videos["duration_seconds"].dropna() / 60
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.hist(minutes.clip(upper=minutes.quantile(0.95)), bins=24,
            color=ACCENT, edgecolor="white")
    ax.set_title("Video duration distribution (95th-percentile capped)")
    ax.set_xlabel("Minutes")
    ax.set_ylabel("Videos")
    sns.despine()
    return _save(fig, charts_dir, "05_video_duration_distribution.png")


def correlation_heatmap(corr, charts_dir):
    if corr is None:
        return None
    fig, ax = plt.subplots(figsize=(7.5, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                vmin=-1, vmax=1, square=True, linewidths=1.5,
                linecolor="white", cbar_kws={"shrink": 0.8}, ax=ax,
                annot_kws={"size": 9})
    ax.set_title("Correlation matrix — available video metrics")
    fig.tight_layout()
    return _save(fig, charts_dir, "06_correlation_heatmap.png")


def views_vs_duration(videos, charts_dir):
    if not {"views", "duration_seconds"} <= set(videos.columns):
        return None
    data = videos.dropna(subset=["views", "duration_seconds"])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(data["duration_seconds"] / 60, data["views"].clip(lower=1),
               s=42, alpha=0.65, color=ACCENT, edgecolors="white",
               linewidths=1.2)
    ax.set_yscale("log")
    ax.set_xscale("log")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_compact))
    ax.set_title("Views vs video duration (log-log)")
    ax.set_xlabel("Duration (minutes)")
    ax.set_ylabel("Views")
    sns.despine()
    return _save(fig, charts_dir, "07_views_vs_duration.png")


def sentiment_distribution(summary, charts_dir):
    if summary is None:
        return None
    fig, ax = plt.subplots(figsize=(7.5, 4))
    order = ["positive", "neutral", "negative"]
    data = summary.set_index("sentiment").reindex(order)
    bars = ax.bar(order, data["count"],
                  color=[SENTIMENT_COLORS[s] for s in order], width=0.55)
    ax.bar_label(bars,
                 labels=[f"{c:,.0f}  ({p}%)" for c, p in
                         zip(data["count"], data["percent"])],
                 padding=4, fontsize=10, color=INK)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_compact))
    ax.set_title("Comment sentiment distribution (VADER)")
    ax.set_ylabel("Comments")
    ax.set_ylim(0, data["count"].max() * 1.18)
    sns.despine()
    return _save(fig, charts_dir, "08_sentiment_distribution.png")


def sentiment_trend(by_day, charts_dir):
    """Sentiment share per approximate day (days-ago buckets, oldest→newest)."""
    if by_day is None or by_day.empty:
        return None
    data = by_day.copy()
    data["label"] = data["days_ago_bucket"].map(
        lambda d: f"~{int(d)}d before scrape" if d > 0 else "scrape day")
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = np.arange(len(data))
    for sentiment in ("positive", "neutral", "negative"):
        if sentiment in data.columns:
            ax.plot(x, data[sentiment], marker="o", markersize=7,
                    linewidth=2, label=sentiment,
                    color=SENTIMENT_COLORS[sentiment],
                    markeredgecolor="white", markeredgewidth=1.5)
    ax.set_xticks(x, data["label"], fontsize=9)
    ax.set_ylabel("Share of comments (%)")
    ax.set_title("Sentiment mix over time (approximate — relative timestamps)")
    ax.legend(frameon=False)
    ax.set_ylim(0, None)
    sns.despine()
    return _save(fig, charts_dir, "09_sentiment_trend_over_time.png")


def comment_volume(by_day, charts_dir):
    if by_day is None or by_day.empty:
        return None
    data = by_day.copy()
    data["label"] = data["days_ago_bucket"].map(
        lambda d: f"~{int(d)}d before scrape" if d > 0 else "scrape day")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    bars = ax.bar(data["label"], data["comments"], color=ACCENT, width=0.6)
    ax.bar_label(bars, labels=[f"{v:,}" for v in data["comments"]],
                 padding=3, fontsize=9, color=INK)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_compact))
    ax.set_title("Comment volume by approximate day")
    ax.set_ylabel("Comments")
    ax.tick_params(axis="x", labelsize=9)
    sns.despine()
    return _save(fig, charts_dir, "10_comment_volume_by_day.png")


def keyword_bars(keywords, charts_dir, source, filename, color=ACCENT):
    if keywords is None or keywords.empty:
        return None
    col = keywords.columns[0]
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.barh(keywords[col], keywords["count"], color=color, height=0.62)
    ax.invert_yaxis()
    ax.bar_label(bars, labels=[f"{v:,}" for v in keywords["count"]],
                 padding=4, fontsize=9, color=INK)
    ax.set_title(f"Top {len(keywords)} {col}s — {source}")
    ax.set_xlabel("Occurrences")
    sns.despine(left=True)
    return _save(fig, charts_dir, filename)


def wordcloud_chart(series, charts_dir, source, filename):
    """Word cloud; skipped silently if the optional dependency is missing."""
    try:
        from wordcloud import WordCloud
    except ImportError:
        return None
    from data_analysis import STOP_WORDS, tokenize
    text = " ".join(
        " ".join(tokenize(t)) for t in series.dropna())
    if not text.strip():
        return None
    wc = WordCloud(width=1400, height=700, background_color="white",
                   colormap="Blues", stopwords=STOP_WORDS,
                   max_words=120, random_state=42).generate(text)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(f"Word cloud — {source}", fontsize=13, fontweight="bold")
    return _save(fig, charts_dir, filename)


def comment_likes_by_sentiment(scored, charts_dir):
    if "comment_likes" not in scored.columns:
        return None
    data = scored[scored["comment_likes"] > 0]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    order = ["positive", "neutral", "negative"]
    sns.boxplot(data=data, x="sentiment", y="comment_likes", order=order,
                palette=SENTIMENT_COLORS, width=0.45, fliersize=2.5,
                linewidth=1, ax=ax)
    ax.set_yscale("log")
    ax.set_title("Comment likes by sentiment (comments with ≥1 like, log axis)")
    ax.set_xlabel("")
    ax.set_ylabel("Likes per comment")
    sns.despine()
    return _save(fig, charts_dir, "13_comment_likes_by_sentiment.png")
