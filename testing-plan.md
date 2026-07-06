# Testing Plan

Two independent suites — backend (pytest) and frontend (Vitest) — each runnable without
Docker and without the full 8000-row dataset.

## Backend — pytest

**Tools**: `pytest`, `httpx` (FastAPI `TestClient`), stdlib `sqlite3`, Pillow (to synthesize
tiny test images).

### Step 1 — Test fixtures & isolation
- Add `backend/requirements-dev.txt`: `pytest`, `httpx`.
- `conftest.py`:
  - `tmp_db` fixture: points `DB_PATH` (via monkeypatch/env) at a temp file per test, calls
    `db.create_schema()` and inserts a small synthetic dataset (~10 rows across all 3 splits,
    tiny solid-color JPEGs generated in-memory with Pillow, varied captions incl. words to
    search on) directly through `db.py` — no parquet/ingestion involved, so tests are fast
    and don't depend on `flickr8k/data` being present.
  - `client` fixture: patches `ingest.ingest` to a no-op (DB is already seeded) and yields a
    `TestClient(app)`.

### Step 2 — Unit tests: `db.py` / `ingest.py`
- `create_schema` creates `samples` + `samples_fts`.
- `_split_from_filename` maps train/validation/test path prefixes correctly, raises/handles
  unknown prefix.
- `_make_thumbnail` output is JPEG, both dimensions ≤ `THUMB_MAX`.
- `db_exists_and_populated()` is `False` on empty DB, `True` after seeding.
- Running `ingest()` twice against a populated DB is a no-op (idempotency).

### Step 3 — API tests: `/api/samples`
- Default call returns `page=0`, correct `total`, `page_size` rows.
- `page`/`page_size` paging: distinct pages don't overlap, last partial page sized correctly.
- `split=train|validation|test` filters correctly; invalid split → `400`.
- `search=` matches rows containing the token in any caption; unmatched term → `total=0`.
- Punctuation-only `search` (e.g. `"!!!"`, no `\w` tokens) → `200`, unfiltered (regression
  test for the FTS empty-token bug already fixed in `main.py`).
- Rows are ordered deterministically by `id`.

### Step 4 — API tests: detail & images
- `GET /api/samples/{id}` → 200 with all 5 (or fewer, if some captions are null) captions.
- `GET /api/samples/{id}` for a missing id → 404.
- `GET /api/images/{id}` and `?thumb=1` → `200`, `content-type: image/jpeg`, thumbnail bytes
  differ from full-image bytes.
- `GET /api/images/{id}` missing id → 404.

### Step 5 — API tests: `/api/sql`
- Valid `SELECT` / `WITH ... SELECT` → 200, correct `columns`/`rows`.
- Rejects non-SELECT (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `PRAGMA`) → 400.
- Rejects multi-statement input (embedded `;`) → 400.
- BLOB columns (`image`, `thumbnail`) are redacted as `"<blob N bytes>"`, never raw bytes.
- Row cap: seed > `MAX_SQL_ROWS` isn't required — instead test with a small
  `MAX_SQL_ROWS` monkeypatched to 2 and confirm `row_count == 2`.
- Invalid SQL syntax → 400 with the sqlite error message surfaced.
- Read-only: confirm the SQL endpoint's connection actually rejects a write (e.g.
  `INSERT` is already blocked at the string-check layer, but also assert the underlying
  read-only connection raises if that check were bypassed).

### Step 6 — Misc
- `GET /api/stats` → correct `total` and per-split counts against the seeded fixture.
- `GET /api/health` → `{"status": "ok"}`.

**Run**: `cd backend && pytest`

---

## Frontend — Vitest + React Testing Library

**Tools**: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`,
`@testing-library/user-event`, `msw` (mock `/api/*` at the network layer instead of
mocking `fetch`/hooks directly), `jsdom` environment.

### Step 1 — Setup
- Add dev deps: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`,
  `@testing-library/user-event`, `msw`, `jsdom`.
- `vite.config.ts`: add a `test` block (`environment: 'jsdom'`, `setupFiles`).
- `src/test/setup.ts`: import `@testing-library/jest-dom`, start/reset/stop an MSW server.
- `src/test/handlers.ts`: MSW handlers for `/api/stats`, `/api/samples`, `/api/samples/:id`,
  `/api/sql`, backed by small fixture JSON (mirrors real API shapes).
- `package.json`: add `"test": "vitest run"`, `"test:watch": "vitest"`.

### Step 2 — Unit tests
- `hooks/useDebounced.ts`: value updates only after the delay (fake timers).
- `api/client.ts`: request URLs/query params are built correctly for
  `fetchSamples({split, search, page, page_size})`; `handle()` throws on a non-OK response.

### Step 3 — Component tests
- `JsonViewer`: given a JS object, rendered output contains the expected keys/values; a
  caption containing `<script>`-like text is rendered as inert text, not an element (the
  library escapes content — this guards against a regression back to raw HTML injection).
- `Toolbar`: split options come from injected stats; typing in search updates the (debounced)
  value passed up; SQL console toggle fires its callback.
- `SamplesTable`: renders one row per sample; clicking a thumbnail, the name, or the JSON
  icon all call `onOpenSample` with that row's id.
- `SampleModal`: closed (`id=null`) renders nothing open; given an id, opens and shows the
  image + a `JsonViewer` of `useSample(id)`'s data; calling `onClose` (via the close button)
  fires the callback.
- `SqlConsole`: typing a query and clicking Run shows a results table; a query rejected by
  the (mocked) API renders an error `Alert`; `null` cells render as `<em>null</em>`.

### Step 4 — Integration test (`App.tsx`)
- Mount `App` with MSW-mocked `/api/stats` + `/api/samples`; assert the table renders
  fixture rows.
- Changing the split dropdown triggers a refetch with the new `split` query param (assert
  via an MSW request-captured spy).
- Typing a search term eventually (after debounce) issues a request with `search=`.
- Clicking "Next page" in `TablePagination` requests `page=1`.
- Clicking a row's JSON icon opens `SampleModal`; clicking a second row's icon while the
  modal is open replaces its content with the second sample (never two modals at once);
  closing the modal returns to the unmodified table/pagination state.

**Run**: `cd frontend && npm test`

---

## Scope notes
- No E2E/browser automation (e.g. Playwright) — out of scope per "keep the scope
  reasonable"; the two unit/integration suites above cover API contract + core UX behaviors
  (search, pagination, JSON detail modal, SQL console safety) without the added infra cost.
- Both suites are wired to run standalone (`pytest`, `npm test`) so they don't depend on
  Docker or the real Flickr8k parquet files being present.
