# Business Insights — Air India Ahmedabad Crash: YouTube Coverage & Sentiment

*All figures below are computed directly from the dataset by `src/run_pipeline.py` and are reproducible from the CSVs in `outputs/tables/`. This report describes media coverage and audience language only — it makes no claims about the cause of the crash.*

## 1. Executive summary

The dataset captures how YouTube news media covered the 12 June 2025 crash of Air India flight AI171 in Ahmedabad: **93 videos from 42 channels totaling 44,975,743 views**, plus **17,838 comments** scraped from one Firstpost video. Coverage was broad but attention was concentrated — the top 5 channels hold 52.2% of all views. Audience comment tone was sombre rather than hostile: 45.3% of comments score negative under VADER, but the dominant language is condolence ("rest peace", "condolences families", "loved ones"), and the most-liked comments per capita are the *positive* ones (hope, gratitude, survivor's "miracle"). Tone stayed stable across the five days covered.

## 2. Data-supported insights

1. **Attention concentrated in a few outlets.** The top 5 of 42 channels (India Today, NDTV, CNN-News18, The Indian Express, CNN) captured **52.2% of the 45.0M total views**; the top 5 individual videos alone took 24.5%.
2. **India Today flooded the zone.** It published **21 of 93 videos (22.6% of all coverage)** — more than the next three channels combined — earning **10,778,558 views**, the most of any channel. Its per-video average (513K) is close to the dataset average (484K): volume, not per-video virality, drove its lead.
3. **Human-story framing led the view counts.** **19 of 93 titles (20.4%) mention the survivor**, and 4 of the top 10 videos by views center the survivor or victims (DD India's survivor interview: 1.90M views; India Today's "Miracle Survivor… Seat 11A": 1.73M).
4. **Short raw-footage clips converted attention most efficiently.** NDTV's 1.1-minute CCTV clip earned **1.55M views per minute of runtime** — the highest in the dataset (views-per-minute is our documented proxy; true engagement rate is not computable, see limitations).
5. **Comment tone: sombre, not hostile.** Of 17,838 comments: **45.3% negative, 29.2% positive, 25.5% neutral** (mean compound −0.102). The top comment bigrams — *rest peace* (391), *condolences families* (229), *loved ones* (224), *god bless* (198) — show the "negative" class is dominated by grief and condolence vocabulary, which VADER scores negative by construction.
6. **Technical speculation is a large, distinct conversation thread.** *boeing* is the #3 comment keyword (1,465 mentions), and *landing gear* (198), *black box* (196), and *pilot error* (191) all rank in the top-10 bigrams — audiences engaged in armchair analysis alongside mourning. (These are description of comment content, not evidence about the crash.)
7. **Positive comments resonate most per comment.** Average likes: **positive 11.0 > negative 9.0 > neutral 5.4**. Uplifting messages (condolence-solidarity, the survivor's story) were the most audience-validated voices in the thread.
8. **Tone was stable across the five scraped days.** The negative share moved only between **42.8% and 48.7%** (buckets ~4 days before scrape → scrape day), with no escalation or recovery trend.

## 3. Trends

- Comment volume peaked ~3 days before the scrape (7,860 comments) and declined toward the scrape day (1,585) — consistent with a breaking-news attention spike, though exact dates are approximations from relative labels.
- Views are heavily right-skewed: median 293K vs mean 484K; a handful of blockbuster uploads (max 3.03M) carry the tail.

## 4. Channel performance

| Rank | Channel | Videos | Total views | Avg views/video |
|---|---|---|---|---|
| 1 | India Today | 21 | 10,778,558 | 513,265 |
| 2 | NDTV | 6 | 4,981,761 | 830,294 |
| 3 | CNN-News18 | 4 | 3,330,577 | 832,644 |
| 4 | The Indian Express | 5 | 2,378,918 | 475,784 |
| 5 | CNN | 2 | 1,997,052 | 998,526 |

Among channels with ≥2 videos, CNN (998K) and CNN-News18 (833K) had the highest per-video averages — international/major outlets earned more per upload, while India Today won on volume.

## 5. Engagement findings

Video-level engagement rate could not be computed (no like/comment counts in the video table). Comment-level engagement shows the pattern in insight 7; the single video with scraped comments (Firstpost, 42,135 views) drew 17,838 comments and 154,454 comment-likes — an unusually deep thread relative to its view count, likely because it covered the PM's site visit and survivor meeting.

## 6. Sentiment findings

Distribution, per-class intensity, trend, and most-liked examples are in `outputs/tables/sentiment_*.csv`. Mean compound within classes: positive +0.526, negative −0.566 — language at both poles is emphatic, as expected for tragedy coverage. **Interpretation guardrail:** VADER measures language tone; the 45.3% negative share reflects mourning vocabulary and criticism of speculation/media style, not a public verdict on any party's culpability.

## 7. Content-topic findings

- **Titles** (n=93): *india, crash, air, ahmedabad, plane, flight* dominate; *survivor* (13 titles' keyword hits) is the leading human-interest term; *live* appears in 19 titles (20.4% used live/breaking framing).
- **Comments** (n=17,838): mourning terms (*god, condolences, sad, families, prayers*) sit alongside technical terms (*boeing, pilot, engine, power, flaps*) — two parallel audience conversations: grief and analysis.

## 8. Recommendations for media analysts & content teams

1. **Human-story angles out-travel technical angles** — survivor/victim framings took 4 of the top 10 slots; plan follow-up coverage around verified human-interest reporting rather than speculation.
2. **Short verified-footage clips are the efficiency winners** (1.55M views/min for the CCTV clip); reserve long formats for live blogs, which earn volume but not density.
3. **Moderate for speculation, not negativity.** The "negative" mass is mostly grief; the actionable moderation surface is the speculation cluster (*pilot error*, *landing gear*, *black box* threads), which risks spreading unverified claims.
4. **Audience-validated tone is compassionate.** The most-liked comments are condolence and solidarity messages — anchoring coverage and community posts in that register matches audience expectations during tragedies.
5. **Fix the collection gap before generalizing sentiment:** scrape comments across many videos/channels (this sample covers one video) before treating tone shares as representative.

## 9. Dataset limitations

- **Comments cover one video only** (Firstpost, `bWO_1UwLh1I`) — sentiment shares must not be generalized to all crash coverage.
- **No video-level likes, comment counts, publish dates, or subscriber counts** — engagement rate, views-vs-likes correlation, and upload-time analyses were skipped (documented in the pipeline's skip log).
- **Timestamps are relative labels** ("3 days ago"), resolved against the 2025-06-16 scrape date; derived dates are approximate to ±1 day.
- **VADER is English-tuned.** Hinglish and non-Latin-script comments (≈0.4% mostly-Devanagari) tend to score neutral; sarcasm and culturally specific mourning idiom are not reliably captured.
- One duplicate video row and 126 duplicate/empty comments were removed (see `outputs/tables/data_quality_summary.csv`).

## 10. Ethical considerations

- This analysis concerns a real tragedy in which 260+ people died. Results are presented to understand media coverage and public discourse — **never** to assign blame or draw conclusions about the crash's cause, which is the mandate of the official AAIB investigation.
- Negative sentiment must not be reported as "public anger at X"; it predominantly encodes grief.
- Comment authors are private individuals; the processed data retains public display handles only, and quoted comments should be used sparingly and respectfully.
- Keyword indicators (e.g., `mentions_boeing`) are descriptive features of the text, not endorsements of the claims within.
