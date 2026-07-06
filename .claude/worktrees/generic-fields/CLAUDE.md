# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local web app for browsing, searching, and inspecting the Flickr8k image-captioning
dataset (8000 images, 5 human captions each) — built for computer-vision researchers.
React + MUI frontend, FastAPI + SQLite backend. See `task.md` for the original assignment,
`plan.md` for the full design/build plan (including a "Revision 2" section documenting the
Turborepo/JSON-modal restructure), and `testing-plan.md` for the (not yet implemented) test
strategy for both sides.

## Commands

Root (Turborepo, fans out to `frontend`/`backend` workspaces):
```bash
npm install          # installs root + both workspaces (npm workspaces)
npm run dev          # turbo run dev   -> vite dev server + uvicorn --reload in parallel
npm run build         # turbo run build -> tsc && vite build (backend build is a no-op)
npm run lint          # turbo run lint  -> eslint (frontend); backend has no linter configured
npm run test          # turbo run test  -> vitest / pytest, once those suites exist
npm run setup         # npm install + setup-dataset:docker + docker:up (the "clone and run" path)
npm run setup-dataset # scripts/setup_dataset.py: verify/move parquet into data/<dataset_name>/
npm run init-db       # turbo init-db -> backend `python -m app.ingest` (needs venv active)
npm run drop-db       # delete the local SQLite DB (docker volume: docker compose down -v)
npm run docker:up|down|logs|init-db   # docker compose wrappers
```
The backend's `dev`/`test`/`lint` scripts (`backend/package.json`) just shell out to
`uvicorn`/`pytest`/etc. — they require `backend/.venv` to already be created and active (or
on `PATH`); Turborepo does not manage the Python environment.

Frontend only (`cd frontend`):
```bash
npm run dev            # vite dev server on :5173, proxies /api -> http://localhost:8000
npm run build           # tsc && vite build
npm run lint            # eslint . --ext ts,tsx --report-unused-disable-directives
```

Backend only (`cd backend`, with venv active):
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.ingest    # one-time: parquet -> backend/data/flickr8k.db (idempotent, safe to rerun)
uvicorn app.main:app --reload --port 8000
```

Docker (the actual "clone and run" path — not Turborepo):
```bash
docker compose up --build   # frontend on :8080 (nginx), backend on :8000
docker compose down         # add -v to also drop the db-data volume and force re-ingestion
```

There is no test suite implemented yet — `testing-plan.md` specifies the intended pytest
(backend) and Vitest+RTL+MSW (frontend) approach in detail; follow it when adding tests
rather than improvising a different structure.

## Architecture

**Data flow**: `data/<dataset_name>/*.parquet` (dataset name from `fields.json`) →
`backend/app/ingest.py` (runs once, on backend
startup, idempotent via `db_exists_and_populated()`) → a single SQLite file
(`backend/data/flickr8k.db` locally, or `/data/db/flickr8k.db` on a named Docker volume) →
served by FastAPI → consumed by the React frontend, entirely through same-origin `/api/*`
calls (proxied by Vite in dev, by nginx in the Docker image).

**Backend** (`backend/app/`) is intentionally a flat, single-file-per-concern FastAPI app,
no ORM:
- `db.py` — `DB_PATH` resolution (env override for Docker), `get_connection()` (normal
  read/write), `get_readonly_connection()` (opens `file:...?mode=ro` — used *only* by the
  `/api/sql` console, never by the app's own read/write paths).
- `fields.py` — loads the repo-root `fields.json`, the single source of truth for the
  dataset's logical columns (see README "Generic by metadata"). Schema, ingestion mapping,
  FTS index, API row shape, and the frontend table all derive from it.
- `ingest.py` — creates the `samples` table (data columns from `fields.json`, plus
  `image`/`thumbnail` BLOBs) and a `samples_fts` FTS5 external-content virtual table
  (`content='samples', content_rowid='id'`) over the `searchable` columns; decodes each image
  with Pillow to get width/height and build a ≤256px JPEG thumbnail (the `derived`-field
  extractors are the only dataset-specific code). Split (`train`/`validation`/`test`) is
  inferred from the parquet filename.
- `main.py` — all routes. Notable non-obvious pieces:
  - `_fts_query()` tokenizes free text into an `AND`-joined FTS5 prefix query; returns `None`
    (not an empty-string query) when there are no `\w+` tokens, so punctuation-only search
    falls back to unfiltered results instead of sending a degenerate MATCH expression.
  - `/api/sql` is deliberately restrictive: only `SELECT`/`WITH`, rejects embedded `;`
    (single statement only), runs on the read-only connection, caps rows at
    `MAX_SQL_ROWS`, and redacts any `bytes`/`bytearray` column value as
    `"<blob N bytes>"` — this is what makes an open SQL console safe to expose in the UI.

**Frontend** (`frontend/src/`):
- `App.tsx` is only a router shell (`react-router-dom`: `/` → `Home`, `*` → redirect to `/`).
  All actual page content lives under `src/pages/` (currently just `Home.tsx`) — put new
  routes there, not in `App.tsx`.
- `Home.tsx` owns all the browse state (split filter, debounced search, pagination, which
  sample id is open in the modal, SQL console open/closed) and wires it into
  `hooks/queries.ts` (React Query hooks; `useSamples` uses `keepPreviousData` for smooth
  paging) and `components/`.
- `components/SamplesTable.tsx` + `components/SampleModal.tsx`: the table is the only browse
  view (there used to be a separate global JSON-view toggle mode; it was removed). Clicking
  a thumbnail/name/JSON icon calls `onOpenSample(id)`, which opens a single `SampleModal`
  instance — "only one sample open at a time" is structural (one modal), not state-tracked.
  `SampleModal` renders JSON via `components/JsonViewer.tsx`, a thin wrapper around
  `@uiw/react-json-view` (collapsible tree) — don't reintroduce a hand-rolled JSON
  highlighter; the previous one used `dangerouslySetInnerHTML` and was deliberately replaced.
  `components/SqlConsole.tsx` is a thin client for `/api/sql`, rendered conditionally from
  `Home.tsx`.
- `api/client.ts` has the only `fetch` calls in the app; all requests are same-origin
  `/api/*` — never hardcode a backend host/port here.

**Monorepo/Docker split**: Turborepo (root `package.json` + `turbo.json`) is a local-dev
convenience layer only. `docker-compose.yml` builds `frontend/` and `backend/` as fully
independent Docker contexts (each has its own Dockerfile and, for the frontend, its own
standalone `package-lock.json` — regenerate it with `cd frontend && npm install
--workspaces=false` if the workspace-hoisted root lockfile ever gets out of sync, since
`npm ci` inside the frontend-only Docker build context needs a self-contained lockfile).
Don't assume changes to the root `package.json`/`turbo.json` affect what Docker builds.
