# Fix Plan — drop/populate, Docker mappings, Datasets page + download nav-guard

## Context

The app was refactored into a layered backend (`app/api`, `app/services`, `app/db`,
`app/models`, `app/bootstrap`). Three problems remain:

1. **Drop → populate doesn't restore data.** `npm run db:drop`
   (`app.registry_cli drop` → `drop_all_data()`) wipes `registry.json` + `data/datasets/`.
   `npm run db:populate` (`app.services.ingest` → `ingest_all_pending()`) then iterates
   `list_dataset_ids()` — which is now empty — and does nothing. `ingest_all_pending()`
   never calls `init_registry()`/`seed_flickr8k_if_needed()`, so Flickr8k is only ever
   re-seeded by the FastAPI `lifespan` on server start. Net effect: `db:drop && db:populate`
   leaves you with no data.

2. **Docker mapping gap.** `docker-compose.yml` mounts only `.../jxie-flickr8k/data` →
   `/data/parquet`. But `bootstrap/seed.py:flickr8k_default_fields()` reads the dataset card
   at `<repo>/datasets/jxie-flickr8k/README.md`, which resolves to `/datasets/...` inside the
   container — not mounted and not copied into the image (`Dockerfile` does `COPY app ./app`
   only). So in Docker, card-based field extraction silently falls back to hard-coded fields.
   (The `explorer-data:/app/data` volume and `PARQUET_DIR` mapping are otherwise correct.)

3. **UX + no download guard.** Desired flow: paste link → fetch schema → two panes
   (left = parquet download progress, right = schema editor) → "Import data" shows a
   *populating DB* status. A dedicated **/datasets** page lists datasets with **Delete**
   (and *continue setup* while still downloading); **no schema editing after import** — the
   schema only configures how the table is displayed, and once imported the user deletes and
   re-adds rather than editing. Today there's no datasets list page (only an AppLayout
   dropdown), and nothing stops the user from navigating away / refreshing mid-download.

### Decisions (from the user)
- Datasets management lives on a **new `/datasets` route** (Home `/` stays the sample browser).
- Navigation is blocked **only during download** (metadata/parquet), not during import.
- **No post-import schema editing** — imported datasets get Delete only; schema is edited
  once, during setup, before import.

---

## Part A — Backend: make drop → populate round-trip work

**`backend/app/registry_cli.py`** — add a `populate` subcommand:
- `populate` → call `init_registry()` (seeds Flickr8k when the registry is empty) then
  `ingest_all_pending()`. Accept an optional `--force` that re-ingests datasets already
  marked `done` (pass through to `ingest_dataset(..., force=True)`).
- Reuse existing functions: `app.services.registry.init_registry`,
  `app.services.ingest.ingest_all_pending` / `ingest_dataset`.

**`backend/app/services/ingest.py`** — make the standalone entry self-seeding:
- In `__main__` (and optionally at the top of `ingest_all_pending()`), call
  `init_registry()` before iterating so `python -m app.services.ingest` also works right
  after a drop. Add a `force` parameter to `ingest_all_pending(force=False)` threaded into
  `ingest_dataset`.

**`backend/package.json`** — point populate at the CLI for consistency with `db:drop`:
- `"db:populate": ".venv/bin/python -m app.registry_cli populate"`.

**`backend/tests/`** — add `test_drop_populate.py`: seed (or ingest) → `drop_all_data()` →
`populate` → assert registry re-seeded and `samples` non-empty. Follow the existing pytest
layout under `backend/tests/`.

## Part B — Docker: fix the card/README mapping

**`docker-compose.yml`** — mount the whole Flickr8k dir so the card is available, and point
`PARQUET_DIR` at its `data` subdir:
```yaml
volumes:
  - ./datasets/jxie-flickr8k:/data/flickr8k:ro
  - explorer-data:/app/data
environment:
  PARQUET_DIR: /data/flickr8k/data
```

**`backend/app/bootstrap/seed.py`** — resolve the README relative to the parquet dir's parent
so it works in both dev and Docker, instead of the hard-coded `../../../datasets/...` path:
- Prefer `os.path.join(os.path.dirname(LEGACY_PARQUET_DIR), "README.md")`
  (`config.LEGACY_PARQUET_DIR`), fall back to the current repo-relative path. Local:
  `.../jxie-flickr8k/data` → parent has `README.md` ✓. Docker: `/data/flickr8k/data` →
  `/data/flickr8k/README.md` ✓.

**Docs** (`README.md`) — note that `npm run db:drop`/`db:populate` are **dev-only** (they call
`.venv/bin/python`, which the backend image doesn't have); the in-container reset stays
`docker compose down -v && docker compose up --build`. Confirm `DATA_ROOT` default (`/app/data`)
and the `explorer-data` volume line up — no change needed there.

## Part C — Frontend: Datasets page, add/schema flow, download guard

**Router migration — `frontend/src/App.tsx`:** switch from `<BrowserRouter>/<Routes>` to
`createBrowserRouter([...]) + <RouterProvider>` so `useBlocker` is available (react-router v7
requires a data router). Routes: `/` → `Home`, `/datasets` → new `Datasets`, `/datasets/new`
→ `AddDataset`, `/datasets/:id/schema` → `SchemaEditor`, `*` → redirect `/`.

**New `frontend/src/pages/Datasets.tsx`** (list/management page):
- `useDatasets()` → table of name / status / row count. Per row:
  - status `done` (imported): **Browse** (set active via `useSetActiveDataset`, go `/`) +
    **Delete** (`useDeleteDataset`, reuse SchemaEditor's confirm dialog). **No Edit.**
  - status not done (fetching/downloading/schema_ready): **Continue setup** →
    `/datasets/:id/schema`.
- **Add dataset** button → `/datasets/new`.
- Add a "Datasets" link in `frontend/src/components/AppLayout.tsx`; the dataset dropdown can stay.

**Add flow — `frontend/src/pages/AddDataset.tsx`:** keep single URL input; on submit poll
`useDownloadStatus`; auto-navigate to `/datasets/:id/schema` on `schema_ready`/`ready`
(already implemented). Guard active only while `fetching_metadata`.

**Two-pane setup — `frontend/src/pages/SchemaEditor.tsx`:** already renders `DownloadPanel`
(left) + fields editor (right) + Import + Delete — keep this as the setup screen. Changes:
- Copy: state that the schema controls table display only, not the source data.
- On **Import data**, surface the "Populating DB…" status (from `useTriggerIngest` /
  `schema.ingest.status`); on `done`, offer Browse.
- This page is reached only during setup (from AddDataset or "Continue setup"); the
  Datasets list does not link imported datasets back here (no post-import editing).

**Download nav-guard — new `frontend/src/hooks/useNavigationGuard.ts`:**
- `useNavigationGuard(active: boolean)` = `useBlocker(active)` (render a MUI confirm dialog
  "Download in progress — leave anyway?") + a `beforeunload` listener while `active`.
- Wire `active` = download in progress only: `AddDataset` (`fetching_metadata`) and
  `SchemaEditor` (`downloading` / `schema_ready`). **Not** active during ingest/import.

---

## Files to modify (summary)
- Backend: `app/registry_cli.py`, `app/services/ingest.py`, `app/bootstrap/seed.py`,
  `package.json`, new `tests/test_drop_populate.py`.
- Docker/docs: `docker-compose.yml`, `README.md`.
- Frontend: `src/App.tsx`, new `src/pages/Datasets.tsx`, `src/components/AppLayout.tsx`,
  `src/pages/AddDataset.tsx`, `src/pages/SchemaEditor.tsx`, new `src/hooks/useNavigationGuard.ts`.

## Verification
1. **Drop/populate:** `cd backend && source .venv/bin/activate`
   `npm run db:drop` → `python -m app.registry_cli list` shows nothing →
   `npm run db:populate` → `list` shows `flickr8k` and its `.db` has rows
   (or hit `/api/datasets/flickr8k/stats`). `pytest tests/test_drop_populate.py`.
2. **Docker mapping:** `docker compose down -v && docker compose up --build`; confirm backend
   logs seed Flickr8k with card-derived fields (5 captions + image) and `/api/datasets`
   returns it ingested; frontend on `:8080` browses samples.
3. **Datasets page + guard:** `npm run dev`. `/datasets` lists datasets with Delete (+
   Continue setup for in-progress). Add a HF dataset: paste URL → schema fetch → two panes;
   try to click a nav link / refresh **during download** → confirm dialog blocks it; after
   parquet completes, Import shows populating status then Browse. Confirm imported datasets in
   `/datasets` expose Delete only (no schema edit).
