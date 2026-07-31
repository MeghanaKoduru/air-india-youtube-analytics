"""
End-to-end pipeline runner.

Usage (from the project root):
    python3 src/run_pipeline.py

Executes every phase in order — inspection, cleaning, feature engineering,
EDA, sentiment analysis, keyword analysis, charts, SQLite load, dashboard
export — then prints the final deliverables summary (schema, KPIs, files
created, skipped analyses).
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
sys.path.insert(0, str(SRC_DIR))

import data_analysis as da  # noqa: E402
import data_cleaning as dc  # noqa: E402
import sentiment_analysis as sa  # noqa: E402
import visualization as viz  # noqa: E402

RAW = PROJECT_ROOT / "data" / "raw"
PROCESSED = PROJECT_ROOT / "data" / "processed"
CHARTS = PROJECT_ROOT / "outputs" / "charts"
TABLES = PROJECT_ROOT / "outputs" / "tables"
DASHBOARD = PROJECT_ROOT / "dashboard"
DB_PATH = PROJECT_ROOT / "air_india_youtube.db"

created_files = []


def save_csv(df, path):
    """Write a CSV and track it for the end-of-run manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    created_files.append(path)


def main():
    # ---------------- Phase 0: inspection ----------------
    print("PHASE 0 — dataset detection & inspection")
    files = dc.find_dataset_files(RAW)
    raw_frames, raw_reports = {}, {}
    for f in files:
        df = dc.load_any(f)
        # Classify each file by its columns, not its name.
        cols = {str(c).lower() for c in df.columns}
        table = "comments" if {"content", "commentid"} & cols else "videos"
        raw_frames[table] = df
        raw_reports[table] = dc.inspect_dataframe(df, f.name)

    # ---------------- Phase 1: cleaning ----------------
    print("\nPHASE 1 — cleaning")
    videos, video_notes = dc.clean_videos(raw_frames["videos"])
    comments, comment_notes = dc.clean_comments(raw_frames["comments"])
    print("video column mapping:", video_notes["column_mapping"])
    print("video fields NOT in dataset:", video_notes["missing_logical_fields"])
    print("comment column mapping:", comment_notes["column_mapping"])

    quality = dc.build_quality_summary(
        raw_reports, {"videos": videos, "comments": comments},
        {"videos": video_notes, "comments": comment_notes})
    save_csv(quality, TABLES / "data_quality_summary.csv")

    # ---------------- Phase 2: features ----------------
    print("\nPHASE 2 — feature engineering")
    videos = da.add_video_features(videos)
    comments = da.add_comment_features(comments)
    save_csv(videos, PROCESSED / "cleaned_youtube_data.csv")
    save_csv(videos, PROCESSED / "video_analysis_data.csv")

    # ---------------- Phase 3: EDA ----------------
    print("\nPHASE 3 — exploratory analysis")
    kpis = da.dataset_overview(videos, comments)
    for k, v in kpis.items():
        print(f"  {k}: {v}")
    save_csv(pd.DataFrame([{"kpi": k, "value": v} for k, v in kpis.items()]),
             TABLES / "dataset_overview_kpis.csv")

    top_by_views = da.top_videos(videos, by="views")
    if top_by_views is not None:
        save_csv(top_by_views, TABLES / "top10_videos_by_views.csv")
    channel_perf = da.channel_performance(videos)
    if channel_perf is not None:
        save_csv(channel_perf, TABLES / "channel_performance.csv")
    corr = da.correlation_matrix(videos)
    if corr is not None:
        save_csv(corr.reset_index().rename(columns={"index": "metric"}),
                 TABLES / "correlation_matrix.csv")
    volume_by_day = da.comment_volume_by_day(comments)

    # ---------------- Phase 4: sentiment ----------------
    print("\nPHASE 4 — VADER sentiment analysis")
    scored = sa.analyze_comments(comments)
    summary = sa.sentiment_summary(scored)
    print(summary.to_string(index=False))
    by_day = sa.sentiment_by_day(scored)
    liked = sa.most_liked_by_sentiment(scored)
    save_csv(scored, PROCESSED / "comment_sentiment_data.csv")
    save_csv(summary, TABLES / "sentiment_summary.csv")
    if by_day is not None:
        save_csv(by_day, TABLES / "sentiment_by_day.csv")
    if liked is not None:
        save_csv(liked, TABLES / "most_liked_comments_by_sentiment.csv")

    # ---------------- Phase 5: keywords ----------------
    print("\nPHASE 5 — text & keyword analysis")
    kw_frames = []
    for source, series in (("video titles", videos.get("title")),
                           ("video descriptions", videos.get("description")),
                           ("comments", scored.get("comment_text"))):
        if series is not None:
            kw = da.top_terms(series, n=20)
            kw.insert(0, "source", source)
            kw_frames.append(kw)
    keywords_all = pd.concat(kw_frames, ignore_index=True)
    save_csv(keywords_all, TABLES / "top_keywords.csv")
    bigrams = da.top_terms(scored["comment_text"], n=20, ngram=2)
    bigrams.insert(0, "source", "comments")
    save_csv(bigrams, TABLES / "top_bigrams.csv")

    # ---------------- Phase 6: charts ----------------
    print("\nPHASE 6 — charts")
    title_kw = keywords_all[keywords_all["source"] == "video titles"].drop(columns="source")
    comment_kw = keywords_all[keywords_all["source"] == "comments"].drop(columns="source")
    chart_calls = [
        viz.top_videos_by_views(videos, CHARTS),
        viz.top_channels_by_views(channel_perf, CHARTS),
        viz.channel_avg_views(channel_perf, CHARTS),
        viz.view_distribution(videos, CHARTS),
        viz.duration_distribution(videos, CHARTS),
        viz.correlation_heatmap(corr, CHARTS),
        viz.views_vs_duration(videos, CHARTS),
        viz.sentiment_distribution(summary, CHARTS),
        viz.sentiment_trend(by_day, CHARTS),
        viz.comment_volume(volume_by_day, CHARTS),
        viz.keyword_bars(title_kw, CHARTS, "video titles",
                         "11_top_keywords_titles.png"),
        viz.keyword_bars(comment_kw, CHARTS, "comments",
                         "12_top_keywords_comments.png", color=viz.ACCENT_2),
        viz.comment_likes_by_sentiment(scored, CHARTS),
        viz.wordcloud_chart(scored["comment_text"], CHARTS, "comments",
                            "14_wordcloud_comments.png"),
        viz.keyword_bars(bigrams.drop(columns="source"), CHARTS, "comments",
                         "15_top_bigrams_comments.png"),
    ]
    for path in chart_calls:
        if path:
            created_files.append(path)
            print(f"  saved {path.name}")

    # ---------------- Phase 7: SQLite ----------------
    print("\nPHASE 7 — SQLite database")
    with sqlite3.connect(DB_PATH) as conn:
        videos.to_sql("videos", conn, if_exists="replace", index=False)
        comments.to_sql("comments", conn, if_exists="replace", index=False)
        scored[["comment_id", "video_id", "comment_text", "comment_likes",
                "days_ago_bucket", "vader_neg", "vader_neu", "vader_pos",
                "vader_compound", "sentiment"]].to_sql(
            "sentiment_results", conn, if_exists="replace", index=False)
        tables = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table'", conn)
    created_files.append(DB_PATH)
    print(f"  tables: {sorted(tables['name'])}")

    # ---------------- Phase 8: dashboard export ----------------
    print("\nPHASE 8 — dashboard data")
    dash = videos.copy()
    dash["has_scraped_comments"] = dash["video_id"].isin(scored["video_id"])
    save_csv(dash, DASHBOARD / "dashboard_data.csv")
    save_csv(scored, DASHBOARD / "dashboard_comments_data.csv")

    # ---------------- Final deliverables summary ----------------
    print("\n" + "=" * 70)
    print("FINAL DELIVERABLES SUMMARY")
    print("=" * 70)
    print(f"cleaned videos shape:   {videos.shape}")
    print(f"cleaned comments shape: {scored.shape}")
    print("\nKPIs:")
    for k, v in kpis.items():
        print(f"  {k}: {v}")
    print("\nSkipped analyses (missing source columns):")
    for analysis, reason in da.skipped:
        print(f"  - {analysis}: {reason}")
    print("\nFiles created:")
    missing_outputs = []
    for f in sorted(set(created_files)):
        ok = Path(f).exists()
        if not ok:
            missing_outputs.append(f)
        print(f"  [{'OK' if ok else 'MISSING'}] {Path(f).relative_to(PROJECT_ROOT)}")
    if missing_outputs:
        raise RuntimeError(f"Expected outputs missing: {missing_outputs}")
    print("\nAll output files verified.")


if __name__ == "__main__":
    main()
