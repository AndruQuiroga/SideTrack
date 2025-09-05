# SideTrack
*A hosted mood/taste analytics pipeline for your music listening history*

> **TL;DR**: Pull listens from ListenBrainz → resolve MusicBrainz metadata → compute audio features + embeddings locally → score tracks on interpretable “vibe axes” (energy, valence, danceability, brightness, pumpiness, etc.) via zero‑shot + light supervision → aggregate to daily/weekly trends → visualize momentum and regime shifts on a beautiful dashboard. Fully containerized; GPU optional.

---

## Why & Goals
You love EDM’s spectrum—from euphoric trance to gritty industrial—and you want a **data-native** view of how your taste evolves. VibeScope creates a personal, privacy‑respecting **taste space** and measures how your listening **moves** through that space over time.

**Core goals**
- Work great on **long‑tail**/underground tracks (minimal reliance on public popularity metadata)
- Run **locally**, offline-friendly (only ListenBrainz/MusicBrainz APIs)
- Provide **interpretable** axes (not just black-box clusters)
- Show **trends & momentum** (are you drifting to darker, faster, more pumpy?)
- Be **modular**: swap models, schedulers, and visualizations

---

## Features (MVP → Pro)
- **Data ingest**: ListenBrainz listens, MusicBrainz entities & relationships (artist ↔ release ↔ track)
- **Audio analysis** (local):
  - Handcrafted MIR features (BPM, key, spectral stats, onset rate, stereo width, dynamics)
  - Learned embeddings (OpenL3/musicnn/PANNs/CLAP)
  - Optional **stem-aware** metrics via Demucs (e.g., *pumpiness*: kick–bass ducking correlation)
- **Mood/taste scoring**:
  - **Zero-shot** text↔audio similarity (e.g., *euphoric*, *driving*, *melancholic*)
  - **Supervised** regressors for valence–arousal–danceability (calibrated later)
  - **Graph smoothing**: label propagation over track/artist/release k‑NN + MB relations
- **Temporal modeling**: weekly centroids, variance, momentum vectors (EMA/Kalman), change‑point alerts
- **Dashboard**:
  - 2D **Taste Trajectory** (UMAP of embeddings with arrows for weekly drift)
  - **Radar** vs 6‑month baseline; **streamgraph** of mood shares; **outlier finder**
  - **Mixtape generator**: pick dominant cluster for a week → curated playlist
- **Auth & Integrations (modern)**:
  - **Google Sign‑In** via Auth.js (NextAuth) in the Next.js UI
  - **ListenBrainz** token connect flow (per‑user)
  - **Last.fm** integration (per‑user) for tag harvesting and scrobble parity
- **No‑label mode** (default): auto‑derive mood axes from zero‑shot + web tags; optional active‑learning UI to add labels gradually
- **Privacy**: store embeddings + features; raw audio stays local
- **Containerized** services; **GPU‑accelerated** when available with automatic **CPU fallback**

---

## Architecture Overview

```
                         ┌───────────────┐     ┌───────────────┐
ListenBrainz  ─────────▶ │  Ingestor     │ ──▶ │ Postgres(+TS) │
MusicBrainz   ─────────▶ │  (API jobs)   │     │  + Vector ext │
                         └──────┬────────┘     └───────┬───────┘
                                │                      │
Local Audio (optional) ─────────┘                      │
                                ▼                      │
                         ┌───────────────┐             │
                         │  Extractor    │  features   │
                         │  (FFmpeg +    │ embeddings  │
                         │  Essentia/NN) ├─────────────┘
                         └──────┬────────┘
                                │ scores
                                ▼
                         ┌───────────────┐
                         │  Scoring      │  (zero-shot +
                         │  + Smoothing  │   supervised)
                         └──────┬────────┘
                                │ aggregates
                                ▼
                         ┌───────────────┐
                         │  API (FastAPI)│ ──▶  UI (Next.js/Plotly)
                         └───────────────┘
```

**Services**
- `db`: Postgres 16 + TimescaleDB; optional pgvector
- `cache`: Redis for queues/rate limiting
- `api`: FastAPI read/write endpoints; serves dashboard config
- `extractor`: batch jobs for audio→features/embeddings
- `scheduler`: calls `/ingest/listens`, `/tags/lastfm/sync`, and `/aggregate/weeks` on a schedule
- `ui`: Next.js app (Plotly / Recharts) for dashboards
- `vectorizer` (optional): hosts CLAP/OpenL3 model if you want a separate container

---

## Data & Schemas

**Tables** (Timescale hypertables where noted):

- `track (track_id, mbid, title, artist_id, release_id, duration, path_local, fingerprint)`
- `artist (artist_id, mbid, name)`
- `release (release_id, mbid, title, date, label)`
- `listen` **(hypertable)** `(user_id, track_id, played_at, source)`
- `features (track_id, bpm, bpm_conf, key, key_conf, chroma_stats jsonb, spectral jsonb, dynamics jsonb, stereo jsonb, percussive_harmonic_ratio, pumpiness)`
- `embeddings (track_id, model, dim, vector)`
- `mood_scores (track_id, axis, method, value, updated_at)`
- `mood_agg_week` **(materialized view)** `(week, axis, mean, var, momentum, sample_size)`
- `labels_user (user_id, track_id, axis, value, created_at)`
- `graph_edges (src_track_id, dst_track_id, weight, kind)`   // kNN + MB relations

**Indices**
- `listen_idx_time`, `listen_idx_track`
- `embeddings_idx` (pgvector)
- `mood_scores_unique (track_id, axis, method)`

---

## Taste Space: Axes & Lexicon

**Continuous axes** (initial set): `energy`, `valence`, `danceability`, `brightness`, `rhythmic_complexity`, `pumpiness`, `texture_density`, `stereo_size`, `tempo`, `mode_confidence`.

**Zero‑shot lexicon** (extendable):
```
euphoric, melancholic, driving, hypnotic, gritty, airy, warm, cold,
aggressive, floaty, groovy, minimal, maximal, industrial, ethereal,
playful, introspective, cinematic, raw, polished
```

---

## Modeling Approaches (choose any combo)

### 1) Handcrafted MIR (transparent, fast)
- **Libs**: `essentia`, `librosa`, `madmom`, `aubio`
- **Metrics**: BPM(+conf), onset rate, spectral centroid/rolloff/flatness, MFCC stats, spectral flux, zero‑crossing, chroma key+mode, loudness & DR, stereo width, percussive/harmonic ratio
- **EDM‑specific**: **pumpiness** = corr(envelope_drums, −envelope_bass) using stems (Demucs) or bandpass proxies

> **What are stems?** Optional source separation (e.g., with **Demucs**) splits a track into drums/bass/other/vocals. We use drum & bass envelopes to estimate side‑chain ducking ("pumpiness"). Enable when GPU is available; disabled by default.

### 2) Learned Embeddings (robust for long‑tail)
- **OpenL3 (music env)**, **musicnn**, **PANNs/CNN14**, **VGGish**, **CLAP**
- Segment (10–30s) or use **full‑track** pooling (default); pool by mean±var (or attention); L2‑normalize

### 3) Zero‑shot Mood Scoring
- With **CLAP** (or text/audio joint model): cosine(track_emb, mood_text_emb)
- No labels required; later calibrate with personal labels (Platt/isotonic)

### 4) Web‑Tag Harvesting (no‑label mode)
- Pull **Last.fm** track/artist tags; normalize with TF‑IDF; map to axes (energy/valence/brightness/etc.) via a learned dictionary
- Use **MusicBrainz** relationships (release/artist/label) to propagate weak labels

### 5) Light Supervision + Personalization (optional)
- Train ridge/MLP from embeddings → (energy/valence/danceability) on public sets (DEAM/EmoMusic, MTG‑Jamendo) and calibrate to you if/when you add labels via the UI

### 6) Graph Label Propagation (stabilize long‑tail)
- kNN over embeddings; add MB relations (same artist/release, remix/comp, label)
- Propagate with weights; Bayesian partial pooling per artist/release

### 7) Temporal Modeling
- Weekly centroid & variance per axis; **momentum** = Δ EMA(4‑week)
- **CUSUM**/Bayesian change‑point for regime shifts
- UMAP(embeddings) → 2D trajectory with arrow glyphs

---

## Pipelines

**A. Ingestion**
1. OAuth sign‑in (Google) via UI; connect **ListenBrainz** and **Last.fm** in settings
2. Pull listens (ListenBrainz token)
3. Resolve MBIDs + fetch artist/release metadata
4. Fetch Last.fm tags for tracks/artists; normalize and cache
5. Build/refresh linkage graph

**B. Audio Feature Extraction** (default: **full tracks**; excerpts optional)
1. Locate local files by MBID/fingerprint; analyze **full audio**; optionally set `EXCERPT_SECONDS` for speed
2. FFmpeg decode → mono/44.1k or stereo as needed
3. Compute MIR + embeddings (OpenL3/musicnn/PANNs/CLAP)
4. Optional: Demucs stems → pumpiness & groove clarity (GPU if available)
5. Store features/embeddings in DB

**C. Scoring & Smoothing**
1. Zero‑shot mood scoring (lexicon)
2. Web‑tag harvesting → axis mapping (no‑label mode)
3. Optional supervised regressors + calibration if you enable active learning later
4. Graph label propagation / partial pooling

**D. Aggregation**
1. Weekly rollups (means, variance, sample count)
2. Momentum vectors (EMA/Kalman)
3. Materialize views for fast UI

**E. Visualization**
- API serves JSON for charts; UI renders Plotly/Recharts components with Auth.js session

## Containerization

### Minimal (MVP) Compose
```yaml
version: "3.9"
services:
  db:
    image: timescale/timescaledb:latest-pg16
    environment:
      - POSTGRES_DB=vibescope
      - POSTGRES_USER=vibe
      - POSTGRES_PASSWORD=vibe
    volumes:
      - db_data:/var/lib/postgresql/data
    ports: ["5432:5432"]

  cache:
    image: redis:7
    ports: ["6379:6379"]

  api:
    build: ./services/api
    env_file: .env
    depends_on: [db]
    ports: ["8000:8000"]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  extractor:
    build: ./services/extractor
    env_file: .env
    volumes:
      - ./data/audio:/audio:ro
    depends_on: [db]
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
    command: python -m extractor.run --schedule "@daily"

  ui:
    build: ./services/ui
    env_file: .env
    depends_on: [api]
    ports: ["3000:3000"]

  proxy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes:
      - ./deploy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on: [ui]

volumes:
  db_data:
  caddy_data:
  caddy_config:
```

> The `extractor` will automatically use GPU when present (NVIDIA runtime) and fall back to CPU otherwise.
```

### Pro Compose (Queues + Scheduler + Vector DB + OAuth‑ready)
```yaml
services:
  vector:
    image: ankane/pgvector
    depends_on: [db]

  scheduler:
    build: ./services/scheduler  # Prefect 2 flows
    env_file: .env
    depends_on: [api, extractor]
    command: python -m scheduler.run

  worker:
    build: ./services/worker      # RQ/Celery worker
    env_file: .env
    depends_on: [cache, db]
    command: rq worker vibescope

  ui:
    environment:
      - NEXTAUTH_URL=${NEXTAUTH_URL}
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - LISTENBRAINZ_APP_NAME=VibeScope
      - LASTFM_API_KEY=${LASTFM_API_KEY}
```

> **Scheduler choice**: using **Prefect 2** as the modern default (switchable to cron if you prefer).yaml
services:
  vector:
    image: ankane/pgvector
    depends_on: [db]

  scheduler:
    build: ./services/scheduler  # Prefect/cron container
    env_file: .env
    depends_on: [api, extractor]
    command: python -m scheduler.run

  worker:
    build: ./services/worker      # RQ/Celery worker
    env_file: .env
    depends_on: [cache, db]
    command: rq worker vibescope
```

### GPU Override (optional)
```yaml
services:
  extractor:
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
    environment:
      - TORCH_DEVICE=cuda
    runtime: nvidia
```

The extractor detects CUDA; if unavailable it falls back to `cpu` automatically.yaml
services:
  extractor:
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
    environment:
      - TORCH_CUDA_ARCH_LIST=All
    runtime: nvidia
```

---

## Service Dockerfiles (sketches)

**`services/extractor/Dockerfile`**
```dockerfile
FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04 AS base
RUN apt-get update && apt-get install -y ffmpeg python3 python3-pip && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false \
 && poetry install --only main
COPY . .
ENV TORCH_DEVICE=auto  # cuda if available else cpu
CMD ["python","-m","extractor.run"]
```

**`services/api/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false \
 && poetry install --only main
COPY ../../Downloads .
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
```

**`services/ui/Dockerfile`**
```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
# Uses Auth.js (NextAuth) for Google OAuth; Tailwind + shadcn/ui + framer-motion
CMD ["pnpm","dev","--","--host","0.0.0.0"]
```

**`deploy/Caddyfile`** (example)
```
:80 {
  redir https://{host}{uri}
}

:443 {
  tls you@example.com
  encode gzip
  handle_path /api/* {
    reverse_proxy api:8000
  }
  handle /* {
    reverse_proxy ui:3000
  }
}
```

---

## Configuration (`.env`)
```
# DB
POSTGRES_HOST=db
POSTGRES_DB=vibescope
POSTGRES_USER=vibe
POSTGRES_PASSWORD=vibe
POSTGRES_PORT=5432

# ListenBrainz / MusicBrainz
LISTENBRAINZ_USER=your_user
LISTENBRAINZ_TOKEN=lb_xxx
MUSICBRAINZ_RATE_LIMIT=1.0   # req/sec

# Last.fm (for web tag harvesting)
LASTFM_API_KEY=lfm_xxx
LASTFM_USER=your_lastfm_username

# Auth.js (NextAuth) – Google OAuth
NEXTAUTH_URL=https://your.domain
NEXTAUTH_SECRET=supersecretlongrandom
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Paths
AUDIO_ROOT=/audio
CACHE_DIR=/tmp/vibescope
EXCERPT_SECONDS=0   # 0 = full tracks; set 30/60 for excerpts

# Models
EMBEDDING_MODEL=openl3,musicnn,clap,panns  # comma‑sep options
USE_CLAP=true
USE_DEMUCS=false
TORCH_DEVICE=auto  # cuda|cpu|auto

# Scheduler intervals (minutes)
INGEST_LISTENS_INTERVAL_MINUTES=1
LASTFM_SYNC_INTERVAL_MINUTES=30
AGGREGATE_WEEKS_INTERVAL_MINUTES=1440
TZ=America/New_York
```

---

## API (FastAPI)
- `GET /health` – service liveness
- `POST /ingest/listens?since=YYYY-MM-DD` – sync listens
- `POST /tags/lastfm/sync?since=YYYY-MM-DD` – fetch & cache Last.fm tags
- `POST /analyze/track/{track_id}` – compute features/embeddings
- `POST /score/track/{track_id}` – compute mood scores
- `POST /aggregate/weeks` – refresh weekly materializations
- `GET /dashboard/trajectory?window=12w` – UMAP positions + arrows
- `GET /dashboard/radar?week=YYYY-WW` – radar data vs baseline
- `POST /labels` – (optional) submit personal labels (axis,value)

**Multi-user note**: API endpoints that read or write user data expect an
`X-User-Id` header identifying the caller.

**Auth model**
- UI uses **Auth.js (NextAuth)** with Google; UI acts as a **BFF proxy** to the API, forwarding an `X-User-Id` header derived from the session. The API authorizes requests per‑user and never stores Google tokens.

---

## Dashboard (Next.js + Plotly/Recharts)
Built with **Next.js 14**, **Tailwind**, **shadcn/ui**, **framer‑motion**, **Plotly** (for arrows/UMAP) and **Recharts** (for streamgraphs). Auth via **Auth.js** (Google provider). Mobile‑friendly.

**Pages**
- `/` – Overview KPIs (listen count, diversity, momentum index)
- `/trajectory` – 2D taste map with weekly arrows; color by energy; tooltip drill‑downs
- `/moods` – streamgraph of mood shares; filters by artist/label/source
- `/radar` – weekly radar vs 6‑month baseline; compare weeks
- `/outliers` – tracks farthest from 90‑day centroid; quick add to playlist
- `/settings` – connect **ListenBrainz** and **Last.fm**; toggle GPU/stems/excerpts

**UI niceties**
- Smooth transitions (framer‑motion), dark/light theme, keyboard nav, persistent filters.

---

## Local Development
```bash
# 1) Copy example env and adjust
cp .env.example .env

# 2) Set up Google OAuth creds
#    - Create a Google Cloud OAuth Client (Web)
#    - Authorized redirect URI: https://your.domain/api/auth/callback/google
#    - Put GOOGLE_CLIENT_ID/SECRET into .env and set NEXTAUTH_URL

# 2b) API base for UI fetches (default: http://localhost:8000)
#     - NEXT_PUBLIC_API_BASE points the Next.js UI at the API
#     - Override in production, e.g., https://api.your.domain

# 3) Build and start
docker compose up -d --build

# 4) Bootstrap DB (migrations, extensions)
docker compose exec api alembic upgrade head

# 5) First sync + analysis
curl -H "X-User-Id: your-user" -X POST http://localhost:8000/ingest/listens?since=2024-01-01
curl -H "X-User-Id: your-user" -X POST http://localhost:8000/tags/lastfm/sync?since=2024-01-01
curl -H "X-User-Id: your-user" -X POST http://localhost:8000/aggregate/weeks

# 6) Open UI
https://your.domain
```

---

## Data Science Details

**UMAP prep**
- Take per‑track embedding; standardize; neighbors=50, min_dist=0.1; fit on full set
- Weekly position = mean of contained tracks → arrow to next week

**Momentum**
- `m_t = EMA(centroid_t, span=4)`; momentum = `m_t − m_{t-1}`

**Change‑points**
- CUSUM on energy/valence; alert when exceeding tuned threshold

**Mixtape selection**
- Dominant cluster (HDBSCAN) of the week; pick k‑medoids with diversity penalty; 60–90 minutes

---

## Options & Swaps
- **Scheduler**: **Prefect 2 (default)** ↔ cron (simple)
- **Queue**: none ↔ RQ ↔ Celery
- **DB**: TimescaleDB only ↔ +pgvector
- **Embeddings**: OpenL3 ↔ musicnn ↔ CLAP ↔ PANNs (you can enable multiple)
- **UI**: Next.js+Plotly (default) ↔ Streamlit (fast) ↔ Dash
- **Audio**: **full tracks (default)** ↔ cached excerpts ↔ stems

---

## Privacy & Licensing
- Raw audio never leaves your machine. Embeddings and features are stored in DB.
- Respect licenses; do not redistribute audio or stems.

---

## Testing
- Synthetic audio fixtures; golden feature vectors
- Deterministic seeds for embeddings/UMAP
- Snapshot tests for API responses and charts

---

## Roadmap
- Smart **vibe summaries** (top words per week) using zero‑shot + tag fusion
- Per‑artist drift and **label influence** diagnostics
- **DJ‑set** segmentation and intra‑track contour plots (post‑v1)
- Export to **ListenBrainz playlists** / local M3U
- Spotify‑style audio features backfill (if you choose to connect their API later)

---

**Rename** the project if you like: *VibeScope*, *TasteTrax*, *Pulseboard*, *Audiograph*, *RhythmLens*. Have fun measuring your vibe. 🎛️
