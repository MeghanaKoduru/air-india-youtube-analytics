# Dashboard Requirements — Air India Ahmedabad Crash: YouTube Coverage & Sentiment

## Data sources (Tableau / Power BI-ready)

| File | Grain | Use for |
|---|---|---|
| `dashboard/dashboard_data.csv` | one row per video (93) | coverage, views, channels, title-keyword flags |
| `dashboard/dashboard_comments_data.csv` | one row per comment (17,838) | sentiment visuals, comment engagement, day trend |

Relate them on `video_id` (1-to-many, videos → comments). Note: only one video has comments, so keep the two fact tables on separate dashboard sections rather than blending measures across them.

## KPI cards

| KPI | Field / calc | Value in current data |
|---|---|---|
| Total videos | `COUNT(video_id)` on videos | 93 |
| Total views | `SUM(views)` | 44,975,743 |
| Unique channels | `COUNTD(channel_name)` | 42 |
| Total comments analyzed | `COUNT(comment_id)` on comments | 17,838 |
| % negative comments | share of `sentiment = "negative"` | 45.3% |
| Mean sentiment (compound) | `AVG(vader_compound)` | −0.102 |

Not buildable from this dataset (source columns absent — do not fake them): Total Likes, video-level Total Comments, Average Engagement Rate.

## Visuals

1. **Top videos by views** — horizontal bar, `title` × `SUM(views)`, top 10, K/M number format.
2. **Top channels by total views** — horizontal bar, `channel_name` × `SUM(views)`, top 10.
3. **Channel efficiency** — scatter: x = video count, y = avg views per video, point = channel; log y recommended.
4. **View distribution** — histogram of `views` (log bins) or box plot.
5. **Sentiment distribution** — bar of `sentiment` counts with % labels. Fixed colors: positive `#2a78d6`, neutral `#a8a69e`, negative `#e34948` (keep this mapping on every visual).
6. **Sentiment trend** — line of sentiment share by `days_ago_bucket` (sort descending so time flows left→right; label axis "approx. days before scrape").
7. **Comment volume by day** — bar on `days_ago_bucket`.
8. **Top keywords** — bar from `outputs/tables/top_keywords.csv` (or import it as a third source), filterable by `source` (titles vs comments).

## Filters (recommended)

- **Channel** (`channel_name`) — applies to video visuals.
- **Sentiment** (`sentiment`) — applies to comment visuals.
- **Approximate day** (`days_ago_bucket`) — comment visuals; label as approximate.
- **Title theme flags** (`mentions_survivor`, `mentions_boeing`, `is_live_or_breaking`) — video visuals.
- Publication date and Engagement Category filters are **not possible** (columns absent) — documented limitation.

## Build steps

**Tableau:** Connect → Text file → add both CSVs; define the `video_id` relationship; create the KPI calcs above as aggregates; build each visual on its own sheet; assemble one dashboard with the sentiment color palette set under *Color → Edit Colors* (assign the three hexes to the sentiment values); add the filters as global quick filters scoped per section.

**Power BI:** Get Data → Text/CSV for both files; Model view → one-to-many on `video_id`; create DAX measures, e.g. `Pct Negative = DIVIDE(CALCULATE(COUNTROWS(comments), comments[sentiment]="negative"), COUNTROWS(comments))`; use conditional formatting / theme JSON for the fixed sentiment colors; slicers for the filter list above.

**Required disclaimer on the dashboard** (place as a text tile): *"Sentiment reflects the tone of comment language (VADER) on one video's comments; it is not representative of all coverage and implies nothing about the cause of the crash. Dates are approximate (derived from relative timestamps vs the 2025-06-16 scrape)."*
