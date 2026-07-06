# Flickr8k Dataset Explorer

A local web tool for browsing, searching, and inspecting the [Flickr8k](https://huggingface.co/datasets/jxie/flickr8k)
image-captioning dataset (8000 images, 5 human captions each).

See [`plan.md`](./plan.md) for the full design/build plan.

## Features

- **Gallery/table view** — paginated grid of id, thumbnail + one column per caption, à la the
  HF dataset viewer; rows-per-page selectable from the toolbar.
- **JSON detail modal** — click a thumbnail, filename, or the JSON icon to open a modal with
  the full-resolution image and an interactive, collapsible JSON tree for that sample.
- **Search** — full-text search across all 5 captions (SQLite FTS5), paginated and debounced.
- **Split filter** — filter by `train` / `validation` / `test`.
- **Dark mode** — toggle in the app bar, persisted across reloads.
- **SQL console** — run arbitrary read-only `SELECT` queries against the SQLite `samples` table
  directly from the UI (image BLOBs are redacted in the response).
- **Generic by metadata** — the dataset's columns are declared once in [`fields.json`](./fields.json)
  and consumed by both backend and frontend; see [Generic by metadata](#generic-by-metadata-fieldsjson).

## Stack

- **Frontend**: React + TypeScript, Vite, MUI 5, styled-components, TanStack React Query,
  React Router, `@uiw/react-json-view`, ESLint.
- **Backend**: Python, FastAPI, SQLite (stdlib `sqlite3`), Pillow (for thumbnails), pandas/pyarrow
  (to read the source parquet files).
- **Data**: the `data/<dataset_name>/*.parquet` files (`data/flickr8k/` for this dataset) are
  ingested once into a local SQLite DB on first backend startup. The dataset name and column
  schema come from `fields.json`.
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

## Generic by metadata (`fields.json`)

The app is **generic by metadata**: the dataset's logical columns are declared once in
[`fields.json`](./fields.json) at the repo root, and both sides consume that single file —
the backend derives the SQLite schema, ingestion mapping, FTS search index, and API row shape
from it, and re-exposes it via `GET /api/fields`; the frontend renders the browse table's
columns from that endpoint. There are no duplicated column definitions in Python and
TypeScript to keep in sync.

```json
{
  "dataset": { "name": "flickr8k", "title": "Flickr8k" },
  "fields": [
    { "key": "captions", "label": "Captions", "type": "string_list",
      "source": "passthrough",
      "source_columns": ["caption_0", "caption_1", "caption_2", "caption_3", "caption_4"],
      "visible": true, "searchable": true }
  ]
}
```

- `dataset.name` — drives the folder layout: parquet files are read from `data/<name>/` and
  the SQLite DB is written to `<name>.db`. `dataset.title` is the UI/API display title.
- `key` / `label` — logical field key (API/JSON) and table column header.
- `type` — `string` | `integer` | `string_list`; drives the SQLite column type and the
  frontend cell renderer (`string_list` renders as an ordered list).
- `source` — `passthrough` copies value(s) verbatim from the parquet column(s) in
  `source_columns` (defaults to `[key]`), **zero code needed to add/remove/rename such a
  field**; `derived` means a small extractor in `backend/app/ingest.py` produces the value
  (e.g. decoding the image for `width`/`height`, parsing the filename for `split`).
- `source_columns` — lets N raw columns collapse into one logical field
  (`caption_0..4` → `captions`).
- `visible` — whether the field gets a column in the browse table.
- `searchable` — whether the field's columns are included in the FTS5 full-text index.
- `role` (optional) — `name` (row display name / modal title) or `split` (rendered as a chip,
  ties into the split filter).

**Scope boundary (deliberate):** `id`, the image/thumbnail BLOBs (+ `/api/images`), and
split-based filtering/stats stay structural — they require dataset-specific code or are core
navigation, not "just another column." Everything else is metadata-driven: pointing the app at
a different image+text dataset means dropping its parquet files in `data/<name>/` and editing
`fields.json` (plus a small extractor only if it needs new *derived* fields).

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
python -m app.ingest        # one-time: data/flickr8k/*.parquet -> backend/data/flickr8k.db
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
| `GET /api/fields` | dataset + field metadata (from `fields.json`) driving the UI |
| `GET /api/stats` | total sample count + counts per split |
| `GET /api/samples?split=&search=&page=&page_size=` | paginated sample list, optional FTS search |
| `GET /api/samples/{id}` | full JSON for one sample |
| `GET /api/images/{id}?thumb=1` | JPEG bytes (thumbnail or full image) |
| `POST /api/sql {"query": "SELECT ..."}` | run a read-only SELECT against `samples` |

## Project layout

```
backend/    FastAPI app, SQLite ingestion, requirements, Dockerfile, package.json (turbo scripts)
frontend/   React + Vite app, Dockerfile, nginx.conf
data/       source parquet datasets, one folder per dataset (data/flickr8k/*.parquet)
fields.json dataset + column metadata — single source of truth for backend and frontend
docker-compose.yml
package.json, turbo.json   root workspace + Turborepo pipeline
plan.md     design/build plan
```
