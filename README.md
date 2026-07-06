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

## Workflow

1. **Add Dataset** (`/datasets/new`) — paste a HuggingFace URL (e.g. `https://huggingface.co/datasets/jxie/flickr8k`)
2. **Schema editor** — fields appear from the dataset card; edit types/visibility while parquet downloads
3. **Import data** — ingest parquet into SQLite (enabled when download is complete)
4. **Browse** (`/`) — select dataset, search, open JSON modal, run SQL

## Quick start

Parquet files are not in the repo — download separately or use **Add Dataset** in the UI.

### Docker (recommended)

```bash
# Optional: pre-download Flickr8k for faster first boot
pip install huggingface_hub
huggingface-cli download jxie/flickr8k --repo-type dataset --local-dir datasets/jxie-flickr8k

docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000/docs
- Optional `HF_TOKEN` env for gated datasets
- Data volume: `explorer-data` → `/app/data` in the backend container
- Stop: `docker compose down`
- **Reset all data**: `docker compose down -v` then `docker compose up --build`

### Local dev

```bash
pip install huggingface_hub
huggingface-cli download jxie/flickr8k --repo-type dataset --local-dir datasets/jxie-flickr8k

cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cd ..
npm install
npm run dev   # backend venv must be active for ingest on startup
```

- Frontend: http://localhost:5173 (proxies `/api` → `http://localhost:8000`)

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

From repo root (requires `backend/.venv`):

```bash
npm run db:drop       # wipe registry + all datasets (schemas, sources, SQLite DBs)
npm run db:populate   # re-ingest registered datasets from parquet (idempotent)
```

`db:drop` runs `python -m app.registry_cli drop` — removes everything under the new multi-dataset layout plus legacy `flickr8k.db`.

**Docker** — reset via volume wipe (no `npm run db:*` inside the container):

```bash
docker compose down -v
docker compose up --build
```

## Delete a single dataset

- **UI**: Schema editor → **Delete dataset** (removes schema, source files, and `{id}.db`)
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
