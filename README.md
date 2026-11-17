# World Talk Brief Studio

An evidence-led upgrade to the supplied WTB automation project. Existing history, website files, channel identity and `python wtb_engine.py` entry point are retained. The old engine is an inactive text backup in `legacy/`.

**Start with [START_HERE_HINDI.md](START_HERE_HINDI.md).** Automatic production remains scheduled at **06:00 and 18:00 UTC: 11:30 AM and 11:30 PM IST**, subject to GitHub scheduling delays. Code pushes run checks only. One documentary and, if its selected excerpt meets duration/QC requirements, one vertical trailer per production run. The five-hour job limit is a ceiling, not a target; internal time budget is 4.5 hours.

## What changed

| Original behavior | New behavior |
|---|---|
| Keyword-triggered effects and forced template rotation | Explicit visual direction for every narration beat |
| Unsourced/random-looking charts | Source excerpts, numerical validation, units, zero baseline and an editorial audit |
| Generic/AI imagery mixed with event reporting | Licensed contextual media with visible archive/stock labels; no AI event images |
| Voice could fall through to gTTS or silence | One provider/voice per video; failures stop production |
| QC exceptions returned success | All QC exceptions block publication and create a report |
| Automatic old-video rehabilitation/channel edits | Only new production; no old-video, comment or channel-branding changes |
| Multiple tokens rotated on quota failures | One authorized channel token; quota errors stop uploading |

## Production path

1. Fresh world/business/science RSS discovery, compared with previous topics; or a manually entered topic.
2. Fetch full readable reporting from at least three domains, then extract facts with verbatim evidence excerpts. A separate AI review checks claim support.
3. Generate an original English documentary: concrete cold open, central question, necessary background, mechanism, evidence/counter-evidence and known/unknown consequences. Target 900–1200 words, 32–44 visual beats, 6–8 chapters. At most two repair attempts.
4. Each beat has its own fact IDs, visual purpose and media query or structured graphic data. Titles and thumbnail claims are checked too.
5. Wikimedia Commons media and optional Pexels clips are matched using subject anchors and a separate relevance judgment. Gemini also inspects sampled image pixels/video frames. Other providers explicitly report metadata-only checks. Set `require_pixel_audit: true` to require Gemini pixel checks.
6. Narration is synthesized to measured per-beat audio, normalized and checked for silence/clipping. Render native 1920×1080/24fps scenes and combine them; Shorts get separate 1080×1920 layouts.
7. Check full video decoding, audio presence, audio/video duration, dimensions, sustained black frames, long silence and actual media duration shares. Default minimum real video: 12%; real media: 35%; failed-media fallback maximum: 25%. Insufficient coverage saves a storyboard and stops before expensive full rendering.
8. Create thumbnail, captions, metadata, credits page and QC reports. Upload only with `--publish` and passing checks. Write the confirmed YouTube video ID immediately into upload receipts.

Graphics include animated charts, timelines, mechanism diagrams, subtle photo motion, full-frame video, a true perspective 3D container illustration, and a schematic globe with Wikipedia-resolved coordinates. The globe has no invented borders, routes or coastlines. 3D is selected only for supported shipment/container explanations; this is not arbitrary photorealistic event reconstruction.

## Keys and configuration

| GitHub Secret | Purpose |
|---|---|
| `YOUTUBE_TOKEN_JSON_B64` | Existing base64 OAuth authorized-user JSON; must allow uploading. Same secret name. |
| `GEMINI_API_KEY` | Existing recommended writing/audit provider; also supports sampled pixel review. |
| `GROQ_API_KEY` or `OPENROUTER_API_KEY` | Alternative writing providers. Free tiers may rate-limit. |
| `DEEPGRAM_API_KEY` | Your existing key now enables Aura-2 English narration. Default: `aura-2-odysseus-en`. |
| `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` | Optional premium voice with provider timing. Use a licensed stock voice or an authorized voice. |
| `PEXELS_API_KEY` | Optional real stock video search; useful when Commons lacks suitable footage. |

Auto voice selection: ElevenLabs when both its secrets exist, otherwise Deepgram if configured, otherwise Edge `en-US-AndrewNeural`. The provider never changes partway through a video. Auto writing selection: Gemini, then Groq, then OpenRouter. Gemini model availability is discovered rather than blindly calling the old model ID.

Optional repository **Variables**: `WTB_LLM_PROVIDER`, `WTB_LLM_MODEL`, `WTB_VOICE_PROVIDER`, `WTB_VOICE`, `WTB_PRIVACY` (`public/unlisted/private`), `YOUTUBE_CHANNEL_ID` (verify token's channel). Defaults are in `studio_config.json`.

Paid provider usage can incur charges. Max AI requests, TTS characters and runtime are bounded in config; these are **not exact dollar caps**. No paid API or YouTube upload was called during local development because your GitHub Secrets were unavailable. The first configured GitHub preview is the external integration test.

Legacy `_2`, `_3`, `_4` token secrets are unused. No OpenAI, Pollinations, Hugging Face or YouTube scraping key is required. Keep credentials in GitHub Secrets, not in code or ZIPs.

## Commands and outputs

Python 3.11+, FFmpeg and ffprobe on PATH; Windows and Linux supported.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p integration_render.py -v
python wtb_engine.py --check
python wtb_engine.py --demo
python wtb_engine.py --topic "A specific documentary topic" --source-url "https://example.org/actual-source"
python wtb_engine.py --publish
```

`--demo` is an offline **fictional graphics demonstration, without narration or publication**. It does not represent premium voice quality or a finished researched documentary.

Production outputs: `documentary.mp4`, optional `short.mp4`, `thumbnail.jpg`, `captions.srt`, `storyboard.json`, `research.json`, `media_credits.json`, `review.html`, QC reports and `run_report.json`. Voice/visual beat timing comes from measured audio duration. ElevenLabs/Edge provider word timings are used when supplied; Deepgram caption timings within a beat are estimated and labeled accordingly.

Background music is optional: specify a licensed local file and its credit in config. Music is ducked under narration. No unlicensed tracks are downloaded automatically.

## Practical limits and recovery

- Automated checks can miss factual, legal or visual errors. Three domains do not guarantee editorial independence. This is a production upgrade, not a guarantee of BBC-level journalism, views, monetization or human-creator quality.
- Commons/Pexels assets are labeled as archive or illustration; they are not authenticated footage of the incident. Missing suitable footage stops production rather than filling the video with unrelated images.
- A source excerpt check proves the words exist, not that the source is true. The separate semantic audit is also AI-based. Review sensitive/current-event reporting.
- Cache is reused locally by content/voice identity. Hosted GitHub jobs start fresh; no cross-run cache recovery is claimed. Interrupted jobs retain reports and GitHub artifacts; they do not resume the whole pipeline automatically.
- Existing homepage, feeds and sitemaps are retained. New source/credit pages are added, but the legacy homepage/feed are not regenerated. The workflow explicitly requests a rebuild of your existing GitHub Pages site after saving credits. Keep Pages configured to the default branch `/docs`; it reports a warning if a rebuild cannot be queued. It does not reconfigure your site.
- A receipt marked `uploading` after a crash is ambiguous. Check YouTube Studio, then record the confirmed ID or clear only the affected entry in `studio_history.json`. If receipt git-push fails, recover `studio_history.json` from the workflow artifact before a retry. Do not blindly rerun ambiguous uploads.
- API availability changes. Use `WTB_LLM_MODEL` to select an available model if discovery fails. Dependencies use bounded version ranges; local tests do not claim external APIs were exercised.

See [UPGRADE_NOTES.md](UPGRADE_NOTES.md) for findings and official references.
