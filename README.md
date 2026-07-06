# Flickr8k Dataset Explorer

A local web tool for browsing, searching, and inspecting the [Flickr8k](https://huggingface.co/datasets/jxie/flickr8k)
image-captioning dataset (8000 images, 5 human captions each).

See [`plan.md`](./plan.md) for the full design/build plan.

## Features

- **Gallery/table view** — paginated grid of thumbnails + captions, à la the HF dataset viewer.
- **JSON detail modal** — click a thumbnail, filename, or the JSON icon to open a modal with
  the full-resolution image and an interactive, collapsible JSON tree for that sample.
- **Search** — full-text search across all 5 captions (SQLite FTS5), paginated and debounced.
- **Split filter** — filter by `train` / `validation` / `test`.
- **SQL console** — run arbitrary read-only `SELECT` queries against the SQLite `samples` table
  directly from the UI (image BLOBs are redacted in the response).

## Stack

- **Frontend**: React + TypeScript, Vite, MUI 5, styled-components, TanStack React Query,
  React Router, `@uiw/react-json-view`, ESLint.
- **Backend**: Python, FastAPI, SQLite (stdlib `sqlite3`), Pillow (for thumbnails), pandas/pyarrow
  (to read the source parquet files).
- **Data**: the `flickr8k/data/*.parquet` files (already present in this repo) are ingested once
  into a local SQLite DB on first backend startup.
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

## Run with Docker (recommended)

Requires Docker + Docker Compose.

```bash
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000/docs (Swagger UI)

The first backend startup ingests all 8000 samples (images + thumbnails) into a SQLite DB stored
in a named Docker volume (`db-data`), so subsequent restarts skip re-ingestion. Ingestion takes
about a minute.

To stop:

```bash
docker compose down
```

(Add `-v` to also delete the ingested SQLite volume, forcing re-ingestion next time.)

## Run locally (without Docker)

**Backend** — create the venv and ingest once, first:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.ingest        # one-time: parquet -> backend/data/flickr8k.db
```

Then, from the repo root, with the backend venv still active in that shell:

```bash
npm install                 # installs root + frontend + backend workspaces
npm run dev                 # turbo run dev -> starts uvicorn (backend) + vite (frontend)
```

Open http://localhost:5173 — Vite proxies `/api` to `http://localhost:8000`.

`npm run build` / `npm run lint` / `npm run test` at the root likewise fan out to both
workspaces via Turborepo. The backend's `dev`/`test` scripts (`backend/package.json`) just
shell out to `uvicorn`/`pytest`, so they require the venv above to be active/on `PATH`;
Turborepo does not manage the Python environment itself.

Alternatively, run each side separately without Turborepo:

```bash
# terminal 1
cd backend && uvicorn app.main:app --reload --port 8000
# terminal 2
cd frontend && npm install && npm run dev
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
backend/    FastAPI app, SQLite ingestion, requirements, Dockerfile, package.json (turbo scripts)
frontend/   React + Vite app, Dockerfile, nginx.conf
flickr8k/   source parquet dataset (already downloaded)
docker-compose.yml
package.json, turbo.json   root workspace + Turborepo pipeline
plan.md     design/build plan
```
