---
title: Content Engine
emoji: 🎬
colorFrom: orange
colorTo: yellow
sdk: docker
app_port: 8000
pinned: false
short_description: Free short-form video generation demo powered by local heuristics and open-source tools
---

# Content Engine

Content Engine is a modular Python pipeline for generating short-form viral videos at scale. It covers idea discovery, virality scoring, script generation, voice synthesis, video assembly, caption packaging, scheduling, and lightweight analytics.

## Project Structure

```text
.
├── .env.example
├── pyproject.toml
├── README.md
├── examples/
│   └── example_output/
│       ├── caption.txt
│       ├── metadata.json
│       └── script.txt
└── src/
    └── content_engine/
        ├── __init__.py
        ├── config.py
        ├── main.py
        ├── models.py
        ├── pipeline/
        │   ├── analytics.py
        │   ├── discovery.py
        │   ├── metadata.py
        │   ├── orchestrator.py
        │   ├── posting.py
        │   ├── script_writer.py
        │   ├── video_assembler.py
        │   ├── visuals.py
        │   └── voice.py
        └── providers/
            ├── llm.py
            ├── trends.py
            └── tts.py
```

## High-Level Plan

1. Discover trends from TikTok, Reddit, and news.
2. Score ideas by hook strength, emotional charge, freshness, and replay potential.
3. Generate a short script with a high-retention structure: hook, tension, payoff.
4. Convert the script to narration audio.
5. Select or synthesize visuals, burn in captions, and render a vertical video with FFmpeg.
6. Package each output with caption copy, hashtags, metadata, and analytics records.
7. Schedule recurring runs and optionally queue platform posting.

## Step-by-Step Implementation

### 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Install FFmpeg and place reusable background clips in `assets/backgrounds/` if you want stock footage instead of the synthetic fallback.

### 2. Configure APIs

Supported integrations:

- Reddit public JSON feeds for `r/AskReddit`, `r/Stories`, and `r/TrueOffMyChest`
- Google News RSS for free topical headlines
- NewsAPI for breaking stories when you explicitly want the paid/API-key path
- A configurable TikTok trend endpoint for scraper/API output
- local heuristic script generation
- `espeak-ng` for free narration
- optional OpenAI-compatible LLM endpoint for script generation
- optional ElevenLabs or OpenAI TTS for narration

The pipeline now defaults to a no-cost mode. If you do not configure paid keys, it still works by using Reddit, Google News RSS, mock seeds, heuristic scripts, generated visuals, and `espeak-ng`.

### 3. Generate One Video

```bash
content-engine run --niche storytime --limit 1
```

This creates a timestamped folder under `output/` containing:

- `script.txt`
- `caption.txt`
- `metadata.json`
- `subtitles.srt`
- `voice.mp3`
- `final.mp4`

### 3B. Run the Website Locally

```bash
content-engine web --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` to use the browser dashboard. The site lets you:

- submit generation jobs
- monitor job status
- preview recent videos
- open scripts, captions, and metadata

### 3C. Run Entirely Free

The default `.env.example` is already configured for free mode:

```bash
FREE_MODE=true
```

That means:

- no OpenAI dependency required
- no ElevenLabs dependency required
- no NewsAPI key required
- no paid hosting required if you deploy to Hugging Face Spaces free tier

### 4. Batch Produce 10-50 Videos Per Day

```bash
content-engine batch --niche confessions --count 12
```

Suggested scaling approach:

- Run 4-8 batches per day with `--count 3` to `--count 8`
- Separate discovery from rendering so one trend pool can feed many variants
- Pre-cache background clips and voice variants
- Run FFmpeg render workers in parallel on a queue
- Store outputs in object storage after local render completes

### 5. Schedule Automation

```bash
content-engine schedule --niche storytime --count 4 --interval-minutes 180
```

This keeps a simple in-process scheduler running. In production, use cron, systemd timers, GitHub Actions, or a queue worker platform.

### 6. A/B Test Hooks

```bash
content-engine run --niche news --limit 1 --ab-hooks 3
```

The script module emits multiple hook variants while sharing the same body and payoff. Track each variant separately in analytics and rotate during posting.

## Key Design Decisions

- Provider boundaries keep unstable APIs isolated from the rest of the system.
- The pipeline degrades gracefully when some APIs are unavailable.
- FFmpeg remains the final renderer because it is reliable, fast, and cheap for volume.
- Analytics are stored as append-only JSONL for easy warehousing later.
- Output folders are self-contained so each video can move through approval and posting independently.

## Example Output

See [examples/example_output/metadata.json](examples/example_output/metadata.json) for a sample package generated by the pipeline.

## Posting and Analytics

The repo includes posting queue scaffolding for TikTok, YouTube Shorts, and Snapchat Spotlight. Real upload calls are left behind provider interfaces because creator account auth flows differ by platform and region.

Analytics tracking records:

- source trend
- niche
- hook variant
- platform
- title
- caption
- publish timestamp
- views
- likes
- comments
- shares
- retention

This is enough to start ranking scripts and hooks by performance.

## Security

Real secrets should never be committed. This repo now includes:

- [`.gitignore`](.gitignore) rules for `.env`, certificates, generated media, and caches
- [`SECURITY.md`](SECURITY.md) with handling guidance
- a GitHub Actions secret scan workflow at [`secret-scan.yml`](.github/workflows/secret-scan.yml)
- a local pre-push style scan command:

```bash
python3 -m content_engine.main security-check
```

## Deploy to a Live Website

The repo now includes a production-ready web app and deployment files:

- [`Dockerfile`](Dockerfile) installs FFmpeg and starts the FastAPI site
- [`render.yaml`](render.yaml) defines a Render web service
- the browser UI lives at [`index.html`](src/content_engine/web/templates/index.html)

### Cheapest Hosting Path

Hugging Face Spaces is the best no-money option for this project because it supports Docker apps and exposes a public URL even on the free tier. Free Spaces can go to sleep when idle, so this is best for a demo or lightweight public tool, not guaranteed always-on production.

### Free Hugging Face Spaces Deploy

1. Create a new Hugging Face Space.
2. Choose `Docker` as the SDK.
3. Upload this repository or sync it from GitHub.
4. Keep the root [`README.md`](README.md) because it now includes the required Spaces YAML metadata.
5. Deploy with no secrets at all for free mode.

Optional environment variables for a safer public demo:

- `FREE_MODE=true`
- `PUBLIC_GENERATION_ENABLED=true`
- `MAX_JOBS_PER_IP=1`
- `JOB_WINDOW_SECONDS=1800`
- `SITE_NAME=Content Engine`

### Deploy Checklist

1. Push this repo to GitHub.
2. Create a Docker Space on Hugging Face.
3. Point it at this codebase.
4. Let the `Dockerfile` build with `ffmpeg` and `espeak-ng`.
5. Open the public Space URL after the build finishes.

### Public Access Notes

The website supports public generation by default. In free mode, the bigger risk is abuse of your tiny free compute budget rather than API spend. For a public demo, you should strongly consider:

- lowering `MAX_JOBS_PER_IP`
- increasing `JOB_WINDOW_SECONDS`
- setting `APP_ADMIN_TOKEN` if you want private access
- disabling `PUBLIC_GENERATION_ENABLED` if you only want personal use
