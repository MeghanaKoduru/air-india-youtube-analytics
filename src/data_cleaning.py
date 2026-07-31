"""
Phase 1 — Data cleaning for the Air India Ahmedabad Crash YouTube dataset.

Responsibilities:
  * Auto-detect the raw dataset files (no hard-coded schema assumptions).
  * Inspect and report structure, missing values, and duplicates.
  * Standardize column names and map them to logical analysis fields.
  * Clean numeric fields (K/M/B suffixes, commas, stray text).
  * Parse relative timestamps ("3 days ago") into approximate datetimes.
  * Clean free-text fields while preserving meaningful words.
  * Produce a data-quality summary CSV.

All functions are defensive: if an expected column is absent the pipeline
skips the dependent step and records the limitation instead of failing.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

# The Kaggle dataset was scraped on this date (it is embedded in the raw file
# names, e.g. "... - 2025-06-16 - comments.xlsx"). Relative timestamps such as
# "3 days ago" are resolved against it, so derived dates are approximate to
# about +/- 1 day.
DEFAULT_REFERENCE_DATE = pd.Timestamp("2025-06-16")

# Candidate raw-column names for each logical field, checked in order after
# column standardization. Extend these lists if the dataset schema changes.
LOGICAL_FIELD_CANDIDATES = {
    "video_id": ["videoid", "video_id", "id"],
    "title": ["title", "video_title"],
    "channel_name": ["author", "channel", "channel_name", "channeltitle"],
    "views": ["viewcount", "views", "view_count"],
    "likes": ["likecount", "likes", "like_count"],
    "comment_count": ["commentcount", "comment_count"],
    "duration_seconds": ["lengthseconds", "duration", "length_seconds"],
    "description": ["shortdescription", "description"],
    "tags": ["keywords", "tags"],
    "published_date": ["publishedat", "published_date", "upload_date", "publishdate"],
    "subscriber_count": ["subscribercount", "subscribers", "subscriber_count"],
    "comment_id": ["commentid", "comment_id"],
    "comment_text": ["content", "comment_text", "text", "comment"],
    "comment_author": ["authorbuttona11y", "author_name", "comment_author"],
    "comment_likes": ["likecountliked", "comment_likes", "votecount", "like_count"],
    "published_relative": ["publishedtime", "published_time", "publishedtimetext"],
    "reply_level": ["replylevel", "reply_level"],
    "reply_count": ["replycount", "reply_count"],
}


def find_dataset_files(raw_dir):
    """Return all tabular data files (xlsx/csv) found in ``raw_dir``.

    Raises FileNotFoundError when the directory holds no candidate files, so
    a misconfigured path fails loudly instead of producing empty analyses.
    """
    raw_dir = Path(raw_dir)
    files = sorted(
        p for p in raw_dir.glob("*")
        if p.suffix.lower() in {".xlsx", ".xls", ".csv"} and not p.name.startswith("~")
    )
    if not files:
        raise FileNotFoundError(f"No .xlsx/.csv dataset files found in {raw_dir}")
    return files


def load_any(path):
    """Load a CSV or Excel file into a DataFrame based on its extension."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def inspect_dataframe(df, name, n_rows=10):
    """Print a structured inspection report and return it as a dict."""
    report = {
        "file": name,
        "rows": len(df),
        "columns": df.shape[1],
        "column_names": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "missing_values": df.isna().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
    }
    print(f"\n=== {name} ===")
    print(f"rows: {report['rows']:,} | columns: {report['columns']}")
    print(f"columns: {report['column_names']}")
    print("dtypes:")
    for c, t in report["dtypes"].items():
        print(f"  {c}: {t}")
    print(f"duplicate rows: {report['duplicate_rows']}")
    print("missing values (non-zero only):")
    for c, m in report["missing_values"].items():
        if m:
            print(f"  {c}: {m:,}")
    print(f"first {n_rows} rows:")
    with pd.option_context("display.max_columns", None, "display.width", 200,
                           "display.max_colwidth", 60):
        print(df.head(n_rows))
    return report


def standardize_columns(df):
    """Lowercase column names, replace spaces with underscores, strip junk."""
    out = df.copy()
    out.columns = [
        re.sub(r"[^a-z0-9_]", "", re.sub(r"\s+", "_", str(c).strip().lower()))
        for c in out.columns
    ]
    return out


def map_columns(df):
    """Map standardized raw columns to logical field names.

    Returns (renamed_df, mapping, missing_fields) where ``missing_fields``
    lists logical fields that could not be found — the caller documents these
    as dataset limitations rather than failing.
    """
    mapping = {}
    for logical, candidates in LOGICAL_FIELD_CANDIDATES.items():
        for cand in candidates:
            if cand in df.columns and cand not in mapping:
                mapping[cand] = logical
                break
    renamed = df.rename(columns=mapping)
    missing = [f for f in LOGICAL_FIELD_CANDIDATES if f not in renamed.columns]
    return renamed, mapping, missing


def clean_numeric(value):
    """Convert messy numeric strings to floats.

    Handles: commas ("1,234"), K/M/B suffixes ("25K" -> 25000,
    "2.5M" -> 2500000, "1.2B" -> 1200000000), surrounding text, and
    missing values (returned as NaN).
    """
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip().replace(",", "")
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*([kKmMbB]?)", text)
    if not match:
        return np.nan
    number = float(match.group(1))
    multiplier = {"k": 1e3, "m": 1e6, "b": 1e9}.get(match.group(2).lower(), 1)
    return number * multiplier


def parse_relative_time(text, reference_date=DEFAULT_REFERENCE_DATE):
    """Parse YouTube relative timestamps ("3 days ago (edited)").

    Returns (approx_datetime, approx_days_ago). Both are NaN/NaT when the
    string cannot be parsed. Resolution is approximate: YouTube rounds its
    relative labels, so a derived date can be off by up to one unit.
    """
    if pd.isna(text):
        return pd.NaT, np.nan
    match = re.search(
        r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s+ago",
        str(text).lower(),
    )
    if not match:
        return pd.NaT, np.nan
    qty = int(match.group(1))
    unit = match.group(2)
    unit_days = {
        "second": 1 / 86400, "minute": 1 / 1440, "hour": 1 / 24,
        "day": 1, "week": 7, "month": 30.44, "year": 365.25,
    }[unit]
    days_ago = qty * unit_days
    return reference_date - pd.Timedelta(days=days_ago), days_ago


def clean_text(text, remove_urls=True):
    """Normalize whitespace, optionally strip URLs; keep meaningful words.

    Deliberately preserves emoji and non-Latin scripts — for sentiment and
    keyword analysis they carry signal (VADER scores many emoji).
    """
    if pd.isna(text):
        return ""
    text = str(text)
    if remove_urls:
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_videos(df, reference_date=DEFAULT_REFERENCE_DATE):
    """Clean the video-details table. Returns (clean_df, notes dict)."""
    notes = {"numeric_converted": [], "datetime_converted": []}
    df = standardize_columns(df)
    df, mapping, missing = map_columns(df)
    notes["column_mapping"] = mapping
    notes["missing_logical_fields"] = missing

    before = len(df)
    df = df.drop_duplicates().copy()
    notes["duplicates_removed"] = before - len(df)

    if "video_id" in df.columns:
        dup_ids = int(df.duplicated(subset="video_id").sum())
        notes["duplicate_video_ids"] = dup_ids
        if dup_ids:
            df = df.drop_duplicates(subset="video_id", keep="first")

    for col in ("views", "likes", "comment_count", "duration_seconds",
                "subscriber_count"):
        if col in df.columns:
            df[col] = df[col].map(clean_numeric)
            notes["numeric_converted"].append(col)

    if "published_date" in df.columns:
        df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")
        notes["datetime_converted"].append("published_date")

    for col in ("title", "description", "tags", "channel_name"):
        if col in df.columns:
            # Keep URLs inside descriptions out of the keyword corpus but do
            # not destroy the text itself for display purposes.
            df[col] = df[col].map(lambda t: clean_text(t, remove_urls=False))

    # Missing-value strategy (documented): numeric metrics stay NaN rather
    # than being imputed with 0 — a missing view count is unknown, not zero.
    # Text fields become empty strings so string operations are safe.
    for col in ("title", "description", "tags", "channel_name"):
        if col in df.columns:
            df[col] = df[col].fillna("")
    return df, notes


def clean_comments(df, reference_date=DEFAULT_REFERENCE_DATE):
    """Clean the comments table. Returns (clean_df, notes dict)."""
    notes = {"numeric_converted": [], "datetime_converted": []}
    df = standardize_columns(df)
    df, mapping, missing = map_columns(df)
    notes["column_mapping"] = mapping
    notes["missing_logical_fields"] = missing

    before = len(df)
    df = df.drop_duplicates().copy()
    notes["duplicates_removed"] = before - len(df)

    # Comments with no text carry no analytical signal — drop and count them.
    if "comment_text" in df.columns:
        df["comment_text"] = df["comment_text"].map(
            lambda t: clean_text(t, remove_urls=True))
        empty = int((df["comment_text"] == "").sum())
        notes["empty_comments_dropped"] = empty
        df = df[df["comment_text"] != ""].copy()

    for col in ("comment_likes", "reply_count"):
        if col in df.columns:
            # Missing like counts mean "no likes shown", i.e. zero.
            df[col] = df[col].map(clean_numeric).fillna(0).astype(int)
            notes["numeric_converted"].append(col)

    if "published_relative" in df.columns:
        parsed = df["published_relative"].map(
            lambda t: parse_relative_time(t, reference_date))
        df["approx_published_date"] = [p[0] for p in parsed]
        df["approx_days_ago"] = [p[1] for p in parsed]
        df["is_edited"] = df["published_relative"].astype(str).str.contains(
            "edited", case=False, na=False)
        notes["datetime_converted"].append(
            "approx_published_date (derived from relative labels)")
    return df, notes


def build_quality_summary(raw_reports, clean_frames, notes_by_table):
    """Assemble the Phase-1 data-quality summary as a tidy DataFrame."""
    rows = []
    for table, raw_report in raw_reports.items():
        clean_df = clean_frames[table]
        notes = notes_by_table[table]
        rows.append({
            "table": table,
            "original_rows": raw_report["rows"],
            "final_rows": len(clean_df),
            "duplicate_rows_removed": notes.get("duplicates_removed", 0),
            "empty_text_rows_dropped": notes.get("empty_comments_dropped", 0),
            "missing_values_before": sum(raw_report["missing_values"].values()),
            "missing_values_after": int(clean_df.isna().sum().sum()),
            "columns_converted_to_numeric": ", ".join(notes["numeric_converted"]) or "none",
            "columns_converted_to_datetime": ", ".join(notes["datetime_converted"]) or "none",
            "unmapped_logical_fields": ", ".join(notes["missing_logical_fields"]) or "none",
        })
    return pd.DataFrame(rows)
