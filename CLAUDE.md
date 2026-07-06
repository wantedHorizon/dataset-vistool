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
uvicorn app.main:app --reload --port 8000
npm run db:drop          # wipe registry + all dataset DBs (python -m app.registry_cli drop)
```

Docker (the actual "clone and run" path — not Turborepo):
```bash
docker compose up --build   # frontend on :8080 (nginx), backend on :8000
docker compose down         # add -v to also drop the db-data volume and force re-ingestion
```

There is a backend pytest suite under `backend/tests/` (mirrors the package layout); the
frontend test suite is still not implemented — `testing-plan.md` specifies the intended
Vitest+RTL+MSW approach in detail.

## Architecture

**Data flow**: HuggingFace parquet (or local seed data) → `services/ingest.py` (runs on
backend startup via `lifespan`, idempotent via `db_exists_and_populated()`) → per-dataset
SQLite files under `backend/data/datasets/{id}.db` → served by FastAPI → consumed by the
React frontend through same-origin `/api/*` calls (proxied by Vite in dev, nginx in Docker).

**Backend** (`backend/app/`) is layered by package, no ORM:
- `config.py` — `DATA_ROOT`, path constants, `MAX_SQL_ROWS`, env overrides.
- `models/` — Pydantic: `dataset.py` (domain schema), `api.py` (request/response DTOs).
- `api/` — FastAPI routers: `datasets.py`, `samples.py`, `sql.py` (thin; no query building).
- `db/` — `connection.py` (SQLite helpers), `columns.py` (canonical schema→column derivation
  shared by ingest and sample queries).
- `services/` — `registry.py` (schema/registry persistence), `ingest.py`, `download.py`
  (HF worker), `query.py` (`fts_query`, `row_to_dict`, WHERE assembly).
- `schema_extraction/` — `card_mapper.py`, `md_parser.py` (HF card → field defs).
- `bootstrap/seed.py` — Flickr8k seeding and legacy-DB migration on first boot.
- `main.py` — app factory, CORS, `lifespan` (registry init + pending ingest), router mount.

Notable behavior preserved from the original flat layout:
- `services/query.py` `fts_query()` tokenizes free text into an `AND`-joined FTS5 prefix
  query; returns `None` when there are no `\w+` tokens.
- `/api/datasets/{id}/sql` is deliberately restrictive: only `SELECT`/`WITH`, rejects `;`,
  read-only connection, caps rows at `MAX_SQL_ROWS`, redacts blob columns.

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
