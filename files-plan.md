# Backend folder & file structure — improvement plan

Status: design doc / plan only (no code changes yet).

## Diagnosis — what's wrong today

The backend has outgrown its flat `app/*.py` layout. What CLAUDE.md still describes as
"flat, single-file-per-concern" now has real coupling and duplication.

### 1. Two confusingly-named model files with overlapping contents
- `dataset_schema.py` holds **both** the domain-config models (`FieldType`, `FieldDef`,
  `SourceConfig`, `SplitConfig`, `JobStatus`, `DownloadStatus`, `DatasetSchema`) **and**
  API request/response models (`CreateDatasetRequest`, `CreateDatasetResponse`,
  `UpdateDatasetRequest`, `DatasetSummary`).
- `schemas.py` re-imports a subset of those and adds more API models (`SamplesPage`,
  `Stats`, `SqlRequest`, `SqlResponse`, `ActiveDatasetResponse`, `ReparseResponse`).
- `main.py` imports `UpdateDatasetRequest` from `dataset_schema` but `CreateDatasetRequest`
  from `schemas` — the split is arbitrary. The names `dataset_schema.py` vs `schemas.py`
  are nearly impossible to tell apart.

### 2. `main.py` (380 lines) mixes routing with business logic
Query-building/serialization helpers (`_fts_query`, `_row_to_dict`, `_searchable_columns`,
`_list_db_columns`, `_has_image_field`) are data-access logic living inside the route module.

### 3. Schema→columns logic is duplicated across `main.py` and `ingest.py`
- `_list_db_columns` (main) and `_db_columns` (ingest) derive SQLite columns from a schema
  with slightly different rules.
- `_searchable_columns` (main) and `_fts_columns` (ingest) both compute FTS columns.

These **must** agree for reads to match writes, but they're two separate implementations —
a real correctness hazard.

### 4. `dataset_registry.py` (273 lines) does four unrelated jobs
Path resolution + registry JSON persistence + schema persistence + status mutation +
**Flickr8k seeding / legacy-DB migration** (`flickr8k_default_fields`,
`seed_flickr8k_if_needed`, `LEGACY_DB_PATH`, `LEGACY_PARQUET_DIR`, `_count_rows`).
Seeding/migration is a one-time bootstrap concern, not registry storage.

### 5. Import graph is tangled with lazy-import workarounds
`db.py` → `dataset_registry`; `dataset_registry` lazy-imports `card_mapper`/`md_parser`
inside functions to dodge cycles; `ingest.py` → both. The lazy imports are a symptom of
layering that isn't expressed in the file structure.

### 6. Minor
- Deprecated `@app.on_event("startup")` (should be a `lifespan` handler).
- `tests/` is flat and only covers 2 of 9 modules (`card_mapper`, `md_parser`).
- `SampleRecord` in `schemas.py` appears unused.

## Proposed target structure

Group by layer inside `app/`, so the dependency direction is explicit
(routes → services → persistence → models):

```
backend/app/
  main.py                  # app factory, middleware, lifespan, router mounting only
  config.py                # DATA_ROOT, paths, MAX_SQL_ROWS, env overrides (one home)

  models/                  # Pydantic — split by role, kill the schema/schemas clash
    __init__.py
    dataset.py             #   domain config: FieldType, FieldDef, SourceConfig,
                           #   SplitConfig, JobStatus, DownloadStatus, DatasetSchema
    api.py                 #   request/response DTOs: Create/Update, SamplesPage,
                           #   Stats, Sql*, ActiveDataset*, Reparse*, DatasetSummary

  api/                     # FastAPI routers — thin, no query building
    __init__.py
    datasets.py            #   registry CRUD, active-dataset, download-status,
                           #   reparse, ingest
    samples.py             #   stats, samples list, sample detail, images
    sql.py                 #   /sql console

  db/
    __init__.py
    connection.py          #   get_connection / get_readonly_connection / get_db_path
    columns.py             #   THE single schema→columns/FTS derivation (see #3),
                           #   shared by ingest (writes) and samples query (reads)

  services/                # business logic, orchestration
    registry.py            #   registry.json + schema.json persistence, status updates
    ingest.py              #   parquet → SQLite
    download.py            #   HF download worker (was hf_download.py)
    query.py               #   _fts_query, _row_to_dict, WHERE building (was in main.py)

  schema_extraction/       # the "figure out fields from a HF card" subsystem
    __init__.py
    card_mapper.py         #   (moved as-is)
    md_parser.py           #   (moved as-is)

  bootstrap/
    seed.py                #   seed_flickr8k_if_needed, legacy DB migration,
                           #   flickr8k defaults

  tests/                   # mirror the package: models/, api/, db/, services/,
                           #   schema_extraction/
```

## Migration plan — incremental, each step independently shippable

Do this as a sequence of small commits rather than one big move, so imports and
`npm run test` stay green throughout.

1. **Split the models (highest value, lowest risk).**
   Create `models/dataset.py` and `models/api.py`, move the classes, and make
   `dataset_schema.py`/`schemas.py` thin re-export shims temporarily. Update imports
   across the app to point at `models`. Delete the shims once nothing references them.
   This alone removes the worst confusion.

2. **Unify column derivation (correctness win).**
   Create `db/columns.py` with one canonical `db_columns(schema)`, `fts_columns(schema)`,
   and `select_columns(schema)`. Delete the duplicated helpers in `ingest.py` and
   `main.py` and have both call the shared module. **Add a test** asserting read-columns
   and write-columns stay consistent — this is the one place a refactor bug would silently
   corrupt data.

3. **Extract query logic out of `main.py`** into `services/query.py` (`_fts_query`,
   `_row_to_dict`, WHERE assembly), then split routes into `api/datasets.py`,
   `api/samples.py`, `api/sql.py`, leaving `main.py` as an app factory that mounts routers
   with a `lifespan` handler (replacing the deprecated `on_event`).

4. **Carve seeding/migration out of `dataset_registry.py`** into `bootstrap/seed.py`;
   rename the rest to `services/registry.py`. Move legacy path constants into `config.py`.

5. **Group `card_mapper.py` + `md_parser.py`** under `schema_extraction/` and
   `hf_download.py` → `services/download.py`. The lazy imports in the old registry can
   likely become top-level once seeding is its own module.

6. **Mirror the layout in `tests/`** and backfill tests for the newly-isolated units
   (registry persistence, column derivation, query building) per `testing-plan.md`.

### Sequencing
Steps 1–2 deliver most of the benefit (name clarity + the duplication/correctness fix) and
are safe to land first. Steps 3–6 are cleanup that can follow.
