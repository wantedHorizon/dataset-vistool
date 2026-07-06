# Flickr8k Dataset Visualization Tool — Plan

A local web tool to browse, inspect, search, and query the **Flickr8k** dataset for
computer-vision researchers.

## Dataset (already downloaded)

`flickr8k/data/*.parquet` — Hugging Face `jxie/flickr8k`.

| split | rows |
|-------|------|
| train | 6000 |
| validation | 1000 |
| test | 1000 |
| **total** | **8000** |

Row schema:
- `image`: `{ bytes: <jpeg>, path: <str> }`
- `caption_0` … `caption_4`: 5 human captions per image

## Tech stack

**Frontend**
- React + TypeScript
- Vite (build/dev)
- MUI 5 (component library)
- styled-components (custom styling)
- @tanstack/react-query (server state, caching, pagination)
- @uiw/react-json-view (interactive/collapsible JSON viewer)
- react-router-dom (routing; `App.tsx` is just the router shell, pages live in `src/pages/`)
- ESLint (lint)

**Backend**
- Python + FastAPI + uvicorn (kept minimal)
- SQLite (single-file local DB)
  - `samples` table with captions, metadata, image BLOB, thumbnail BLOB
  - `samples_fts` FTS5 virtual table for caption full-text search
- One-time ingestion script parquet → SQLite

**Infra**
- Docker + docker-compose (backend + frontend behind nginx, one command)
- Turborepo (root `npm run dev|build|lint|test`, orchestrates the frontend/backend
  workspaces for local dev; Docker Compose remains the single "run everything" path)

## Features

1. **Table/Gallery mode** — like the HF dataset viewer: paginated rows, each with an
   image thumbnail + the 5 captions. Split selector.
2. **JSON detail modal** — click an image's name/thumbnail, or a dedicated button, to
   open a modal with the full-res image and an interactive, collapsible JSON tree for
   that sample. Being a modal, only one sample's detail is ever shown at a time.
3. **Search** — full-text caption search (SQLite FTS5), paginated.
4. **Pagination** — server-side, page + page_size.
5. **SQL query mode** — a text box to run read-only `SELECT` queries against the DB and
   view results in a table (BLOB columns are redacted for safety/size).
6. **Stats** — small dataset summary (counts per split) for orientation.

---

## Steps

### Step 1 — Repo layout
```
mb2/
  plan.md
  README.md
  docker-compose.yml
  flickr8k/data/*.parquet        # dataset (present)
  backend/
    Dockerfile
    requirements.txt
    app/
      main.py                    # FastAPI app + routes
      db.py                      # sqlite connection helpers
      ingest.py                  # parquet -> sqlite (run once / on boot)
      schemas.py                 # pydantic models
  frontend/
    Dockerfile
    nginx.conf
    package.json
    tsconfig.json
    vite.config.ts
    .eslintrc.cjs
    index.html
    src/
      main.tsx                   # QueryClient + MUI theme providers, renders <App />
      App.tsx                    # router shell (BrowserRouter + Routes)
      pages/
        Home.tsx                 # the dataset browser (toolbar, table, pagination, SQL console)
      api/client.ts              # fetch wrapper + types
      hooks/                     # react-query hooks
      components/                # SamplesTable, SampleModal, JsonViewer, SqlConsole, Toolbar
      theme.ts
```

### Step 2 — Backend: DB + ingestion
- `db.py`: open SQLite (path from env), row factory, read-only connection helper for SQL console.
- `ingest.py`:
  - create `samples` (id, split, image_path, caption_0..4, width, height, image BLOB, thumbnail BLOB)
  - create FTS5 `samples_fts(caption_0..4)` mirroring `samples`
  - stream each parquet split, decode image with Pillow to get size + build a ~256px thumbnail, insert.
  - idempotent: skip if DB already populated.

### Step 3 — Backend: API (FastAPI)
- `GET /api/stats` → `{ total, splits: {train, validation, test} }`
- `GET /api/samples?split&page&page_size&search` → `{ total, page, page_size, rows: [...] }`
  (rows carry id, split, captions, image_url, thumb_url; FTS when `search` set)
- `GET /api/samples/{id}` → full row JSON (for detail/JSON panel)
- `GET /api/images/{id}?thumb=0|1` → image / thumbnail bytes
- `POST /api/sql { query }` → `{ columns, rows }`; only single `SELECT`, blob columns redacted, row cap.
- CORS enabled for dev.

### Step 4 — Frontend scaffold
- Vite + React + TS, MUI5 theme provider, styled-components, React Query provider, ESLint config.
- `api/client.ts` typed wrappers for the endpoints above.

### Step 5 — Frontend: browse experience
- `Toolbar`: split selector, search box, page size, **View mode toggle** (Table / JSON),
  **SQL console** toggle.
- `SamplesTable` (Table mode): MUI Table; columns = thumbnail, id/name (clickable), captions.
  Clicking name expands `RowDetail` (single open row, JSON of that sample).
- `JsonList` (JSON mode): each row rendered as pretty JSON card.
- `Pagination`: MUI TablePagination driven by server `total`.
- React Query hooks with `keepPreviousData` for smooth paging.

### Step 6 — Frontend: SQL console
- `SqlConsole`: textarea (prefilled example), Run button, results MUI table, error display.

### Step 7 — Docker
- `backend/Dockerfile`: python slim, install deps, run ingestion-on-boot then uvicorn.
- `frontend/Dockerfile`: build with node, serve static via nginx, proxy `/api` → backend.
- `docker-compose.yml`: mounts `flickr8k/` and a `db` volume; `docker compose up` → app on `:8080`.

### Step 8 — Docs
- `README.md`: prerequisites, Docker one-liner, and local (non-Docker) dev instructions.

## Design notes
- Server-side pagination + thumbnails keep the UI fast over 8000 images.
- FTS5 gives real search without any external search service.
- SQL console is read-only + blob-redacted → useful for researchers, safe by construction.
- Modular: API client, hooks, and components are decoupled so new views/columns are easy to add.

---

## Revision 2 — Turborepo + dynamic JSON viewer + JSON-in-modal

Changes requested: add Turborepo to orchestrate the repo, swap the hand-rolled JSON
highlighter for a real dynamic JSON-viewer library, remove the global Table/JSON view-mode
toggle, and replace the inline single-row-expand with a button that opens a modal.

### Step 9 — Turborepo
- Root `package.json`: `"workspaces": ["frontend", "backend"]`, `devDependencies: { turbo }`,
  scripts `dev`/`build`/`lint`/`test` each delegating to `turbo run <task>`.
- Root `turbo.json`: pipeline for `dev` (`cache: false`, `persistent: true`), `build`
  (`dependsOn: ["^build"]`, `outputs: ["dist/**"]`), `lint`, `test` (no cacheable outputs).
- `backend/package.json` (new, thin wrapper so the backend is a turbo workspace too):
  scripts `dev` → `uvicorn app.main:app --reload --port 8000`, `test` → `pytest`,
  `lint` → `ruff check .` (or a no-op if no Python linter is added), `build` → no-op.
  Caveat to document in README: this assumes `backend/.venv` is already created and active
  (or the scripts are pointed at `.venv/bin/python`) — turbo just orchestrates the command,
  it doesn't manage the Python environment.
- Root `.gitignore`: add `.turbo/` and the root `node_modules/`.
- Docker is unaffected — `docker-compose.yml` keeps building each service independently;
  Turborepo is a local-dev convenience layer (`npm run dev` at the root replaces running
  `uvicorn` and `vite` in two separate terminals), not the "one command" path required by the
  assignment (that's still `docker compose up`).

### Step 10 — Dynamic JSON viewer library
- Add `@uiw/react-json-view` (typed, themeable, collapsible tree, React 18-compatible) as a
  frontend dependency.
- Delete `frontend/src/components/JsonBlock.tsx` (the regex-highlighter that used
  `dangerouslySetInnerHTML`) — this also removes the only such usage in the codebase.
- Add `frontend/src/components/JsonViewer.tsx`: thin wrapper around the library, collapsed
  by default below depth 2, in a scrollable container, themed to match the app.

### Step 11 — Revert the global JSON view mode
- `Toolbar.tsx`: remove the `ViewMode` type/export, the `viewMode`/`onViewModeChange` props,
  and the Table/JSON `ToggleButtonGroup`.
- `App.tsx`: remove `viewMode` state and the `JsonList` import/usage; drop the corresponding
  props passed into `Toolbar`.
- Delete `frontend/src/components/JsonList.tsx`.
- `SamplesTable` (renamed conceptually to just "the browse table") becomes the only view.

### Step 12 — "View JSON" button + modal
- `SamplesTable.tsx`: drop the `openId`/`onToggle` inline-accordion plumbing and the extra
  detail `<TableRow>`. Add a per-row button (thumbnail/name still clickable too) that calls
  a new `onOpenSample(id)` prop.
- Add `frontend/src/components/SampleModal.tsx` (replaces `RowDetail.tsx`): an MUI `Dialog`
  keyed on `id: number | null`, showing the full-res image + `JsonViewer` for `useSample(id)`,
  with the existing loading/error handling. Delete `RowDetail.tsx`.
- `App.tsx`: replace `openId`/`handleToggleRow` with `activeId`/`setActiveId`; render a
  single `<SampleModal>` instance. "Only one open at a time" becomes structural (one modal
  instance) rather than `openId`-equality bookkeeping.

### Step 13 — Docs
- Update the Features list above (JSON view mode → JSON detail modal; row detail → modal).
- Update `README.md` (turborepo root commands, updated feature list) and
  `testing-plan.md` (drop `JsonList`/`JsonBlock`/`RowDetail` test cases, add
  `JsonViewer`/`SampleModal` cases, update the `SamplesTable` test to check that the button
  opens the modal rather than toggling an inline row).

### Design notes
- Turborepo's real value here is a single `npm run dev|build|lint|test` at the root with
  caching; Docker Compose remains the actual "one command runs everything" path.
- A collapsible, searchable JSON tree is more useful to a researcher inspecting nested
  sample data than a static highlighted `<pre>` block, and drops the codebase's one
  `dangerouslySetInnerHTML` usage.
- A modal makes "only one open at a time" a structural property instead of something enforced
  by state comparisons, and keeps the table's row height stable while browsing.
