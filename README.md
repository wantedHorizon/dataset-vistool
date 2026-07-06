# Dataset Explorer

A local web tool for browsing, searching, and inspecting HuggingFace datasets — starting with
[Flickr8k](https://huggingface.co/datasets/jxie/flickr8k) (8000 images, 5 human captions each).

Add any HuggingFace parquet dataset by URL: the app downloads it, parses the README for field
structure, lets you edit field types and visibility, then ingests into SQLite for fast browse/search.

See [`plan.md`](./plan.md) for the full design/build plan.

## Features

- **Add datasets by URL** — paste a HuggingFace dataset link; parquet + README are downloaded automatically.
- **Schema editor** — review fields parsed from the dataset README; set types, table visibility, and searchability.
- **Gallery/table view** — paginated grid of thumbnails + fields, à la the HF dataset viewer.
- **Dataset selector** — switch between ingested datasets on the browse page.
- **JSON detail modal** — click a thumbnail, filename, or the JSON icon to open a modal with
  the full-resolution image and an interactive, collapsible JSON tree for that sample.
- **Search** — full-text search across searchable fields (SQLite FTS5), paginated and debounced.
- **Split filter** — filter by train / validation / test (when splits are present).
- **SQL console** — run arbitrary read-only `SELECT` queries against the SQLite `samples` table
  directly from the UI (image BLOBs are redacted in the response).

## Quick start

The parquet files (~1.1 GB) are not in the repo — download them first, then run.

### Docker (recommended)

```bash
# Optional: pre-download Flickr8k for faster first boot (otherwise use Add Dataset in the UI)
pip install huggingface_hub
huggingface-cli download jxie/flickr8k --repo-type dataset --local-dir datasets/jxie-flickr8k

docker compose up --build
```

- Frontend: http://localhost:8080 — use **Add Dataset** to paste a HuggingFace URL, edit the schema, then **Import data**
- Backend API: http://localhost:8000/docs (Swagger UI)
- Optional `HF_TOKEN` env for gated datasets
- Stop: `docker compose down`
- Reset all data: `docker compose down -v` then `docker compose up --build`

### Local dev

```bash
# 1. Download dataset
pip install huggingface_hub
huggingface-cli download jxie/flickr8k --repo-type dataset --local-dir datasets/jxie-flickr8k

# 2. Backend venv + populate DB
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cd ..
npm install
npm run db:populate

# 3. Start dev servers (venv must be active)
npm run dev
```

- Frontend: http://localhost:5173 (Vite proxies `/api` to `http://localhost:8000`)

## Stack

- **Frontend**: React + TypeScript, Vite, MUI 5, styled-components, TanStack React Query,
  React Router, `@uiw/react-json-view`, ESLint.
- **Backend**: Python, FastAPI, SQLite (stdlib `sqlite3`), Pillow (for thumbnails), pandas/pyarrow
  (to read the source parquet files).
- **Data**: `datasets/jxie-flickr8k/data/*.parquet` (download separately — see [Quick start](#quick-start)) are ingested
  once into a local SQLite DB on first backend startup.
- **Monorepo tooling**: Turborepo orchestrates `frontend`/`backend` as npm workspaces for local
  dev (`npm run dev|build|lint|test` from the repo root). Docker Compose remains the single
  "clone and run" path — Turborepo is a convenience layer on top of it, not a replacement.

Everything runs on a single machine with open-source tools only — no cloud services, managed
databases, hosted search, or paid APIs.

## Why these features

Judgment calls made with a CV researcher's workflow in mind:

- **Search over captions (FTS5)** — the fastest way to find samples matching a concept (e.g.
  "dog running") without scrolling through thousands of thumbnails.
- **SQL console** — researchers often want one-off slices (e.g. samples with a given caption
  length, or per-split counts) that a fixed UI can't anticipate; a safe, read-only console covers
  the long tail of ad-hoc questions without building bespoke filters for each one.
- **Collapsible JSON tree in a modal** — makes the exact schema/shape of each record explicit
  (useful when writing code against the dataset), while keeping the underlying grid intact so
  you can close the modal and keep browsing/comparing exactly where you left off.
- **Dataset stats (per-split counts)** — a quick sanity check when first loading an unfamiliar
  dataset.

## Download the dataset

Used in [Quick start](#quick-start) above. The files land in `datasets/jxie-flickr8k/data/`.

**Option A — Hugging Face CLI (recommended)**

```bash
pip install huggingface_hub   # provides huggingface-cli
huggingface-cli download jxie/flickr8k --repo-type dataset --local-dir datasets/jxie-flickr8k
```

**Option B — curl (no HF install)**

```bash
mkdir -p datasets/jxie-flickr8k/data
BASE=https://huggingface.co/datasets/jxie/flickr8k/resolve/main/data
for f in \
  test-00000-of-00001-42a2661d12c73e48.parquet \
  train-00000-of-00002-2f8f6bfa852eac4b.parquet \
  train-00001-of-00002-2173151d8cd6c7fb.parquet \
  validation-00000-of-00001-7025a2b596f14b7b.parquet
do
  curl -L -o "datasets/jxie-flickr8k/data/$f" "$BASE/$f"
done
```

## Run with Docker

Requires Docker + Docker Compose. Follow the [Quick start](#quick-start) steps, or if the dataset
is already downloaded:

```bash
docker compose up --build
```

On first startup the backend ingests all 8000 samples into a SQLite DB in the `db-data` Docker
volume (~1 min). Subsequent `up` restarts skip re-ingestion.

- `docker compose up` — populates the DB on **first** startup (or after a volume wipe)
- `docker compose down` — stops containers but **keeps** the DB volume
- `docker compose down -v` — deletes the DB volume; next `up` re-ingests from parquet

## Run locally

Follow the [Quick start](#quick-start) steps above. Additional notes:

`npm run build` / `npm run lint` / `npm run test` at the root fan out to both workspaces via
Turborepo. The backend's `dev`/`test` scripts shell out to `uvicorn`/`pytest`, so they require
the venv to be active — Turborepo does not manage the Python environment.

Alternatively, run each side separately:

```bash
# terminal 1
cd backend && uvicorn app.main:app --reload --port 8000
# terminal 2
cd frontend && npm install && npm run dev
```

## Database commands

**Local dev** (from repo root; requires `backend/.venv`):

```bash
npm run db:populate   # ingest parquet -> SQLite (idempotent)
npm run db:drop       # delete backend/data/flickr8k.db
npm run db:drop && npm run db:populate   # force full re-ingest
```

**Docker** — there is no `npm run db:*` equivalent. To drop and re-populate:

```bash
docker compose down -v
docker compose up --build
```

## API overview

| Endpoint | Description |
|---|---|
| `GET /api/stats` | total sample count + counts per split |
| `GET /api/samples?split=&search=&page=&page_size=` | paginated sample list, optional FTS search |
| `GET /api/samples/{id}` | full JSON for one sample |
| `GET /api/images/{id}?thumb=1` | JPEG bytes (thumbnail or full image) |
| `POST /api/sql {"query": "SELECT ..."}` | run a read-only SELECT against `samples` |

## Project layout

```
backend/              FastAPI app, SQLite ingestion, requirements, Dockerfile, package.json (turbo scripts)
frontend/             React + Vite app, Dockerfile, nginx.conf
datasets/jxie-flickr8k/   source parquet dataset (download separately)
docker-compose.yml
package.json, turbo.json   root workspace + Turborepo pipeline
plan.md     design/build plan
```
