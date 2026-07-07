# Dataset Explorer

A local web tool for browsing, searching, and inspecting HuggingFace datasets — starting with
[Flickr8k](https://huggingface.co/datasets/jxie/flickr8k) (8000 images, 5 human captions each).

Add any HuggingFace parquet dataset by URL: the app fetches the dataset card metadata, downloads
parquet in the background, lets you edit field types and visibility, then ingests into SQLite for
fast browse/search.

See [`plan.md`](./plan.md) for the full design/build plan.

## Features

- **Add datasets by URL** — paste a HuggingFace dataset link; schema is extracted from the dataset card (YAML/API) while parquet downloads.
- **Schema editor** — review and edit fields (type, table visibility, searchability); re-extract from card.
- **Gallery/table view** — paginated grid of thumbnails + fields, à la the HF dataset viewer.
- **Dataset selector** — switch between ingested datasets on the browse page.
- **JSON detail modal** — click a thumbnail, filename, or the JSON icon for full-res image + JSON tree.
- **Search** — full-text search across searchable fields (SQLite FTS5).
- **Split filter** — filter by train / validation / test (when splits are present).
- **SQL console** — read-only `SELECT` queries against the `samples` table (BLOBs redacted).

## Quick start

**Recommended — Docker (one command).** No Python venv, Node install, or `npm install` on your machine. Clone the repo and run:

```bash
docker compose up --build
```

When the build finishes, open **http://localhost:8080**. Frontend and backend start together; data persists in the `explorer-data` volume.

| | |
|---|---|
| App | http://localhost:8080 |
| API docs | http://localhost:8000/docs |
| Stop | `docker compose down` |
| Reset all data | `docker compose down -v` then `docker compose up --build` |

For gated HuggingFace datasets: `HF_TOKEN=hf_… docker compose up --build`.

## How to use

Parquet files are not in the repo — add datasets through the UI (or pre-download Flickr8k for local dev; see [Download the dataset](#download-the-dataset-manual)).

1. **Add dataset link and download** — open **Add Dataset** (`/datasets/new`), paste a HuggingFace URL (e.g. `https://huggingface.co/datasets/jxie/flickr8k`), and click **Add Dataset**. The app fetches the dataset card, extracts fields, and downloads parquet in the background. You are redirected to the schema editor when metadata is ready.
2. **Choose schema** — on the schema editor (`/datasets/{id}/schema`), review fields extracted from the dataset card. Set each field's type, table visibility, and searchability; click **Save schema** if you change anything. Parquet may still be downloading — progress is shown in the side panel.
3. **Populate the DB** — when the download finishes, click **Import data** (saves schema first if needed). The app ingests parquet into SQLite; the button shows **Populating DB…** while running.
4. **Browse your dataset** — click **Browse dataset** or go to **Browse** (`/`). Use the dataset selector in the toolbar to switch between imported datasets. Search, filter by split, open the JSON modal on a row, or run read-only SQL.

Resume an in-progress dataset from **Datasets** (`/datasets`) — open **Schema** for datasets still downloading or not yet imported.

## Local development (without Docker)

Use this path if you are **contributing** or want hot reload. It needs more setup than Docker: Python 3.9+, Node.js 18+, npm, and a backend virtualenv.

**One-time setup** (from repo root):

```bash
# Optional: pre-download Flickr8k so first boot seeds a dataset immediately
pip install huggingface_hub
huggingface-cli download jxie/flickr8k --repo-type dataset --local-dir datasets/jxie-flickr8k

# Python backend
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..

# Frontend + Turborepo
npm install
```

**Start dev servers** (from repo root, with the backend venv active):

```bash
source backend/.venv/bin/activate    # required — turbo invokes uvicorn from your PATH
npm run dev
```

- App: http://localhost:5173 (Vite dev server; `/api` proxied to the backend)
- API docs: http://localhost:8000/docs

**Alternative — two terminals** (no need to keep venv active in the frontend terminal):

```bash
# Terminal 1 — backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

On first startup the backend creates `backend/data/`, seeds Flickr8k if `datasets/jxie-flickr8k/data/` exists, and ingests any pending datasets.

**Reset / re-ingest** (venv active, from repo root):

```bash
npm run db:drop       # wipe all datasets
npm run db:populate   # re-seed registry + re-ingest from parquet
```

**Gated HuggingFace datasets:** set `HF_TOKEN` in your shell before starting the backend.

## Data layout

Explorer state lives under `backend/data/` (or `/app/data` in Docker):

```
backend/data/
  registry.json              # dataset list + active dataset id
  datasets/
    {id}/schema.json         # field schema, download/ingest status
    {id}/source/             # downloaded parquet + README (HF add flow)
    {id}.db                  # ingested SQLite (one file per dataset)
```

Pre-downloaded parquet for local dev can also live at `datasets/jxie-flickr8k/data/` (not deleted by `db:drop`).

## Database commands

From repo root (**dev-only** — requires `backend/.venv`; not available inside the Docker backend image):

```bash
npm run db:drop       # wipe registry + all datasets (schemas, sources, SQLite DBs)
npm run db:populate   # re-seed Flickr8k when empty, then re-ingest from parquet
```

`db:drop` runs `python -m app.registry_cli drop` — removes everything under the new multi-dataset layout plus legacy `flickr8k.db`.
`db:populate` runs `python -m app.registry_cli populate` — calls `init_registry()` then ingests pending datasets.

In Docker, reset via volume wipe instead (no `npm run db:*` inside the container): `docker compose down -v && docker compose up --build`.

## Delete a single dataset

- **UI**: Datasets page (`/datasets`) or schema editor during setup → **Delete**
- **API**: `DELETE /api/datasets/{id}`

## API overview

| Endpoint | Description |
|----------|-------------|
| `GET /api/datasets` | List datasets (id, name, download/ingest status) |
| `POST /api/datasets` | Add dataset by HuggingFace URL |
| `GET /api/datasets/{id}` | Full schema + status |
| `PUT /api/datasets/{id}` | Save edited schema |
| `DELETE /api/datasets/{id}` | Delete dataset (schema, source, DB) |
| `GET /api/datasets/{id}/download-status` | Download/schema progress |
| `POST /api/datasets/{id}/ingest` | Ingest parquet → SQLite |
| `POST /api/datasets/{id}/schema/reparse` | Re-extract fields from dataset card |
| `GET /api/active-dataset` | Active dataset id |
| `PUT /api/active-dataset` | Set active dataset |
| `GET /api/datasets/{id}/stats` | Total + per-split counts |
| `GET /api/datasets/{id}/samples` | Paginated browse + FTS search |
| `GET /api/datasets/{id}/samples/{sample_id}` | One sample as JSON |
| `GET /api/datasets/{id}/images/{sample_id}?thumb=1` | JPEG bytes |
| `POST /api/datasets/{id}/sql` | Read-only SQL console |

## Stack

- **Frontend**: React + TypeScript, Vite, MUI 5, TanStack React Query, React Router, `@uiw/react-json-view`
- **Backend**: Python, FastAPI, SQLite, Pillow, pandas/pyarrow, huggingface_hub
- **Monorepo**: Turborepo (`npm run dev|build|lint|test`); Docker Compose for single-command run

## Download the dataset (manual)

Files land in `datasets/jxie-flickr8k/data/`:

```bash
pip install huggingface_hub
huggingface-cli download jxie/flickr8k --repo-type dataset --local-dir datasets/jxie-flickr8k
```

## Project layout

```
backend/                 FastAPI, registry, ingest, card_mapper, Dockerfile
frontend/                React + Vite, Dockerfile, nginx.conf
datasets/jxie-flickr8k/  optional local parquet (gitignored)
docker-compose.yml       explorer-data volume for /app/data
package.json, turbo.json Turborepo root
plan.md                  design/build plan
```
