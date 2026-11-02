# WTB News Engine

## Production schedule

- GitHub Actions checks twice an hour at 17 and 47 minutes India time. A saved cadence marker allows a full video batch only once every two hours; a missed check gets another chance in about 30 minutes.
- A normal batch targets two long documentaries and two linked vertical Shorts (four uploads). If a run publishes only part of its batch, the next half-hour check can fill the gap.
- Code pushes do not start production. Use **Run workflow** for an immediate manual run; automatic production remains schedule-driven.
- GitHub scheduled events are best-effort. The run summary and `output/wtb_1080p_report.json` distinguish videos rendered from videos YouTube confirmed as uploaded.

## Editorial and visual checks

- Geopolitics is selected from global news sources and must pass a topic/category match before it can enter that slot.
- Video visuals must pass source-resolution and topic-match checks. The pre-upload gate blocks short, malformed, low-resolution, or visually unsupported outputs and writes per-video QC reports.
- The engine uses original WTB graphics and branding. It does not promise to reproduce another channel's exact editing style.

## YouTube quota notes

- Video uploads use the YouTube API's separate daily upload bucket. Captions, thumbnails, and localization writes use other quota limits and may be skipped when those budgets run low.
- The workflow aims for 48 uploads/day only when all 12 two-hour batches complete and YouTube confirms every upload; it does not bypass API or platform limits.
