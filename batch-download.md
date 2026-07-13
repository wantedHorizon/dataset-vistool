# batch-download.md

Plan for **batch download** of samples: multi-row selection, "download all", and
"download by range", all honoring the active split + search filter. Output is a ZIP
containing image JPEGs plus a metadata file.

This doc is split so a **backend agent** and a **frontend agent** can work in parallel.
The **Shared Contract** section is the interface both sides build against — implement it
exactly and the two halves integrate without further coordination.

---

## Goals

1. **Multi-row select** — checkboxes per row + a header "select page" checkbox, and a
   "select all N matching the filter" affordance that spans pages (not just loaded rows).
2. **Download all** — every sample matching the current split + search filter.
3. **Download by range** — a position window over the filtered set (e.g. results
   101–500, ordered by `samples.id`), intersected with the current filter.
4. All three respect the active **split + search** filter.
5. Download payload = a `.zip` with image JPEGs + a `metadata.jsonl` manifest.

### Decisions already made
- **Payload**: ZIP = images + metadata (JSONL manifest). Not images-only, not metadata-only.
- **Range semantics**: position in the filtered set (offset window over results ordered by
  `samples.id`), *not* raw sample-id range.
- The existing `SamplesPage.total` (unbounded `COUNT(*)` over the filter) is already the
  correct "amount of results" — the frontend "select all" and range max come from it. No
  count change is required; the work is a new download endpoint + selection UI.

---

## Shared Contract (both agents build to this)

### New endpoint

```
POST /api/datasets/{dataset_id}/download
Content-Type: application/json
```

Request body (`DownloadRequest`):
```jsonc
{
  "mode": "filter",          // "ids" | "filter"
  "split": "train",          // optional; applies in BOTH modes as an extra AND filter
  "search": "dog running",   // optional; applies in BOTH modes (same FTS as browse)

  // mode === "ids":
  "ids": [12, 55, 890],      // explicit sample ids (from checkbox selection)

  // mode === "filter":
  "offset": 100,             // optional; 0-based position window start
  "limit": 400               // optional; window size. omit both => ALL matching rows
}
```

Semantics:
- `mode: "ids"` → download exactly those ids (still AND-ed with `split`/`search` if present,
  so a stale selection can't leak filtered-out rows). Used by "download selected".
- `mode: "filter"` with no `offset`/`limit` → "download all" matching the filter.
- `mode: "filter"` with `offset`/`limit` → "download by range" (positions ordered by
  `samples.id`, same ordering as the browse table).
- Enforce `MAX_DOWNLOAD_ROWS` (see backend plan). If the resolved selection exceeds it,
  return **413** with `{ "detail": "..." }` (frontend surfaces this message).

Response: `200` streaming `application/zip`, header
`Content-Disposition: attachment; filename="{dataset_id}-samples.zip"`.

ZIP layout:
```
images/{id}.jpg          # one per sample that has image bytes
metadata.jsonl           # one JSON object per sample, same shape as GET /samples rows
                         #   minus blob columns, plus "image_file": "images/{id}.jpg"
                         #   (image_file omitted when the sample has no image)
```

Errors: `404` unknown dataset, `413` too many rows, `400` on bad params / sqlite error —
all as `{ "detail": string }`, matching existing routes so `api/client.ts` `handle()` works.

---

## Backend agent plan

Scope: FastAPI only. No frontend files.

### Files
- `backend/app/models/api.py` — add `DownloadRequest` (and enum for `mode`).
- `backend/app/config.py` — add `MAX_DOWNLOAD_ROWS = 2000` (tunable; guards zip size/memory).
- `backend/app/services/download_zip.py` *(new)* — resolve selection → stream a ZIP.
- `backend/app/api/samples.py` — add the `POST .../download` route (thin; delegates to the
  service). Reuse `build_samples_where`, `select_columns`, `row_to_dict`, `has_image_field`.
- `backend/tests/` — new `test_download.py`.

### Implementation notes
1. **Selection resolution** (build one `WHERE`/params, mirroring `list_samples`):
   - Start from `build_samples_where(search, split)` for the filter clause.
   - `mode: "ids"` → additionally `AND samples.id IN (?,?,…)`. Chunk if the id list is large
     (SQLite param limit ~999) or use a temp table / `json_each` on a bound JSON array.
   - `mode: "filter"` with range → append `ORDER BY samples.id LIMIT ? OFFSET ?`.
   - Always `ORDER BY samples.id` so range positions match the browse table exactly.
2. **Count guard**: run the same `COUNT(*)` first; if `> MAX_DOWNLOAD_ROWS` → `HTTPException(413)`.
3. **Streaming**: use `zipstream`-style or Python's `zipfile.ZipFile` writing to a
   `SpooledTemporaryFile`, returned via `StreamingResponse`. Prefer a generator that yields
   zip chunks so memory stays bounded (8000 blobs must not be held at once). Fetch rows with
   a server-side cursor / batched `fetchmany`, pulling the full image blob column (the browse
   `select_columns` intentionally omits blobs — write a dedicated SELECT that includes the
   image field for this route).
4. **metadata.jsonl**: for each row, `row_to_dict(row, schema, dataset_id)` gives the
   browse-shaped dict (already blob-free, includes group text_list captions). Add
   `image_file` when the sample has image bytes. Write one compact JSON line per sample.
5. **Image bytes**: read the image blob column (not `thumbnail`) → `images/{id}.jpg`. Skip
   `image_file` for rows whose blob is NULL. If the schema has no image field, still produce
   a valid ZIP with just `metadata.jsonl`.
6. Keep the route **thin** per the repo's layering rule (routers don't build queries) —
   query assembly + zip generation live in `services/download_zip.py`.

### Tests (`backend/tests/test_download.py`)
- `mode: "ids"` returns a zip whose `metadata.jsonl` has exactly those ids; images present.
- `mode: "filter"` (no range) matches `list_samples` total for the same split/search.
- `mode: "filter"` range `offset/limit` returns the same id slice the browse table would.
- `search`/`split` narrow both modes; stale id outside the filter is excluded in `ids` mode.
- Over-limit selection → 413.
- Dataset with no image field → zip with only `metadata.jsonl`.
- Unknown dataset → 404.

### Manual verification
```bash
curl -s -X POST localhost:8000/api/datasets/flickr8k/download \
  -H 'Content-Type: application/json' \
  -d '{"mode":"filter","search":"dog","limit":5}' -o out.zip
unzip -l out.zip
```

---

## Frontend agent plan

Scope: React/MUI only. Build against the Shared Contract; do not wait on the backend —
the endpoint shape above is fixed.

### Files
- `frontend/src/api/client.ts` — add `DownloadRequest` type + `downloadSamples(datasetId, req)`
  that POSTs, reads the response as a `Blob`, and triggers a browser save (object URL +
  temporary `<a download>`; revoke the URL after). Reuse `handle()`'s error extraction for
  non-2xx (parse `detail` before treating the body as a blob).
- `frontend/src/hooks/queries.ts` — `useDownloadSamples()` mutation wrapping the client call
  (exposes `isPending`/`error` for button state + snackbar).
- `frontend/src/components/SamplesTable.tsx` — add a leading checkbox column: header
  checkbox (select/deselect the current page, indeterminate when partial) and a per-row
  checkbox. New props: `selectedIds: Set<number>`, `onToggleRow`, `onTogglePage`,
  `allPageSelected`. Clicking a checkbox must **not** open the sample modal (stop propagation).
- `frontend/src/components/DownloadBar.tsx` *(new)* — appears when there is a selection or on
  demand: shows "{n} selected", a **Download selected** button, a **Download all (N filtered)**
  button, and a **Download range…** button that opens a small dialog (from/to position inputs,
  validated against `total`). Includes the "select all N matching this filter" link (Gmail
  style) that switches selection into `selectAllMatching` mode spanning pages.
- `frontend/src/pages/Home.tsx` — own the selection state and wire it up.

### Selection state (in `Home.tsx`)
- `selectedIds: Set<number>` — explicit per-row picks (from loaded pages).
- `selectAllMatching: boolean` — when true, "download all/range" uses `mode: "filter"` with
  the current `split`/`search`; individual checkboxes fall back to `mode: "ids"`.
- Reset selection whenever `activeDatasetId`, `split`, or `search` changes (a changed filter
  invalidates the selection). Page changes keep the selection.
- Show the true match count from `data.total` (already correct) in "Download all (N)" and as
  the range max.

### Wiring the three actions → `downloadSamples`
- **Download selected** → `{ mode: "ids", ids: [...selectedIds], split, search }`.
- **Download all** → `{ mode: "filter", split, search }` (no offset/limit).
- **Download by range** → `{ mode: "filter", split, search, offset: from-1, limit: to-from+1 }`
  (dialog inputs are 1-based positions; convert to 0-based `offset`).
- Disable buttons + show a spinner while `isPending`. On 413/error, show the `detail` message
  in an MUI `Alert`/snackbar.

### UX notes
- Keep the checkbox column `fixed`-style (always visible, not toggle-able via the column menu).
- Large downloads: the browser holds the whole zip blob in memory before saving — acceptable
  for a local research app, but keep `MAX_DOWNLOAD_ROWS` in mind and surface the 413 clearly.

### Tests (per `testing-plan.md`, once the suite exists)
- Selecting rows enables "Download selected" with the right count.
- Header checkbox toggles the whole page; "select all matching" flips to filter mode.
- Changing search/split clears the selection.
- Range dialog validates against `total` and sends the right `offset`/`limit`.
- MSW mock asserts the request body for each of the three actions.

---

## Sequencing / integration

1. Both agents start immediately against the Shared Contract; no ordering dependency.
2. Frontend can develop against an MSW mock of `POST .../download` returning a small zip.
3. Integration check: `npm run dev`, pick a filter, exercise all three actions, confirm the
   downloaded `metadata.jsonl` ids match what the browse table shows for the same filter/range.

## Risks / open items
- **Memory/size**: streaming on the backend keeps server memory bounded, but the browser
  buffers the full blob. `MAX_DOWNLOAD_ROWS = 2000` is a starting guard — revisit if "download
  all 8000" is a hard requirement (would need a true streamed-to-disk download, e.g. a GET link
  for filter mode instead of fetch+blob).
- **Id list size** in `mode: "ids"`: chunk or use `json_each` to stay under SQLite's param cap.
- **Filename collisions**: `images/{id}.jpg` uses the unique sample id, so no collisions even
  if an original filename field repeats.
