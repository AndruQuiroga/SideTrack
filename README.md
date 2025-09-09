# SideTrack

Hosted mood/taste analytics for your music listening history.

Pull listens from ListenBrainz → resolve MusicBrainz metadata → compute audio features/embeddings locally → score tracks on interpretable axes → aggregate to weekly trends → visualize in a dashboard. Fully containerized; GPU optional.

---

## Services

- db: Postgres 16 + TimescaleDB (primary store)
- cache: Redis 7 (queues, rate limiting)
- api: FastAPI
- extractor: audio features/embeddings (Librosa + optional models)
- scheduler: periodic calls (ingest, tags sync, aggregates)
- worker: background jobs (RQ)
- ui: Next.js dashboard
- proxy: Caddy reverse proxy

---

## Containerization

Single Docker Compose with all services enabled.

- File: `compose.yml`
- Build the shared base image:
```
docker build -f services/base/Dockerfile -t sidetrack-base .
```

- Start everything:

```bash
docker compose up -d --build
```

The extractor uses GPU automatically when available (NVIDIA runtime), and falls back to CPU.

---

## Quick Start

```bash
# 0) Clone and enter
git clone https://github.com/AndruQuiroga/SideTrack.git
cd SideTrack

# 1) Configure environment
cp .env.example .env
# (Optional) set LASTFM_API_KEY, DEFAULT_USER_ID, and NEXT_PUBLIC_API_BASE if needed

# 2) Build the base image
docker build -f services/base/Dockerfile -t sidetrack-base .

# 3) Start the stack (single compose)
docker compose up -d --build

# 4) Apply DB migrations
docker compose exec api alembic upgrade head

# 5) Pull listens and aggregate (replace YOUR_USER)
curl -H "X-User-Id: YOUR_USER" -X POST "http://localhost:8000/api/v1/ingest/listens?since=2024-01-01"
curl -H "X-User-Id: YOUR_USER" -X POST "http://localhost:8000/tags/lastfm/sync?since=2024-01-01"
curl -H "X-User-Id: YOUR_USER" -X POST "http://localhost:8000/aggregate/weeks"

# 6) Open the UI
open http://localhost:3000
# Production: https://sidetrack.network
```

Developer tooling (optional):

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install pre-commit
pre-commit install && pre-commit run --all-files
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
LISTENBRAINZ_USER=your_user          # ListenBrainz username for ingestion
LISTENBRAINZ_TOKEN=lb_xxx            # ListenBrainz API token
MUSICBRAINZ_RATE_LIMIT=1.0   # req/sec

# Last.fm
LASTFM_API_KEY=lfm_xxx
LASTFM_API_SECRET=lfm_secret

# Auth.js (NextAuth) – Google OAuth
NEXTAUTH_URL=https://sidetrack.network
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
- `POST /api/v1/ingest/listens?since=YYYY-MM-DD` – sync listens
- `GET /api/v1/listens/recent?limit=50` – most recent listens
- `POST /tags/lastfm/sync?since=YYYY-MM-DD` – fetch & cache Last.fm tags
- `POST /analyze/track/{track_id}` – compute features/embeddings
- `POST /score/track/{track_id}` – compute mood scores
- `POST /aggregate/weeks` – refresh weekly materializations
- `GET /api/v1/dashboard/trajectory?window=12w` – UMAP positions + arrows
- `GET /api/v1/dashboard/radar?week=YYYY-WW` – radar data vs baseline
- `POST /labels` – (optional) submit personal labels (axis,value)

### API versioning

Endpoints are prefixed with `/api/{version}`. The current stable version is
`v1`; requests to `/` redirect to `/api/v1`. Unversioned paths are deprecated
and will be removed in a future release. Clients should update any calls such as
`/ingest/listens` to `/api/v1/ingest/listens` to ensure compatibility.

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
#    - Authorized redirect URI: https://sidetrack.network/api/auth/callback/google
#    - Put GOOGLE_CLIENT_ID/SECRET into .env and set NEXTAUTH_URL

# 2b) API base for UI fetches (default: http://localhost:8000)
#     - NEXT_PUBLIC_API_BASE points the Next.js UI at the API
#     - Override in production, e.g., https://sidetrack.network/api

# 3) Build the base image
docker build -f services/base/Dockerfile -t sidetrack-base .

# 4) Start the stack (single compose)
docker compose up -d --build

# 5) Bootstrap DB (migrations)
docker compose exec api alembic upgrade head

# 6) First sync + analysis
curl -H "X-User-Id: your-user" -X POST http://localhost:8000/api/v1/ingest/listens?since=2024-01-01
curl -H "X-User-Id: your-user" -X POST http://localhost:8000/tags/lastfm/sync?since=2024-01-01
curl -H "X-User-Id: your-user" -X POST http://localhost:8000/aggregate/weeks

# 7) Open UI (default port)
http://localhost:3000
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

- **Scheduler**: simple Python scheduler (current) ↔ cron
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

**Rename** the project if you like: _VibeScope_, _TasteTrax_, _Pulseboard_, _Audiograph_, _RhythmLens_. Have fun measuring your vibe. 🎛️
