"""FastAPI backend for the generic dataset explorer."""
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .dataset_registry import (
    delete_dataset,
    get_active_dataset_id,
    list_summaries,
    load_schema,
    save_schema,
    set_active_dataset_id,
    source_dir,
)
from .dataset_schema import DatasetSchema, FieldType, UpdateDatasetRequest
from .db import ensure_registry, get_connection, get_readonly_connection
from .hf_download import start_download
from .ingest import ingest_dataset
from .md_parser import parse_readme
from .schemas import (
    ActiveDatasetResponse,
    CreateDatasetRequest,
    CreateDatasetResponse,
    DatasetSummary,
    ReparseResponse,
    SamplesPage,
    SqlRequest,
    SqlResponse,
    Stats,
)

app = FastAPI(title="Dataset Explorer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_SQL_ROWS = 500


@app.on_event("startup")
def _startup() -> None:
    ensure_registry()
    from .ingest import ingest

    ingest()


def _fts_query(search: str) -> Optional[str]:
    tokens = re.findall(r"\w+", search)
    if not tokens:
        return None
    return " AND ".join(f'"{t}"*' for t in tokens)


def _has_image_field(schema: DatasetSchema) -> Optional[str]:
    for f in schema.fields:
        if f.type == FieldType.image:
            return f.name
    return None


def _row_to_dict(row: sqlite3.Row, schema: DatasetSchema, dataset_id: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"id": row["id"]}
    keys = row.keys()

    for f in schema.fields:
        if f.type == FieldType.split:
            if "split" in keys:
                data["split"] = row["split"]
            continue
        if f.type == FieldType.text_list and f.group_members:
            members = [row[m] for m in f.group_members if m in keys and row[m] is not None]
            data[f.name] = members
            continue
        if f.name in keys and f.type not in (FieldType.image, FieldType.blob):
            data[f.name] = row[f.name]

    if "width" in keys and row["width"] is not None:
        data["width"] = row["width"]
    if "height" in keys and row["height"] is not None:
        data["height"] = row["height"]

    image_field = _has_image_field(schema)
    if image_field and image_field in keys and row[image_field] is not None:
        data["image_url"] = f"/api/datasets/{dataset_id}/images/{row['id']}"
        data["thumb_url"] = f"/api/datasets/{dataset_id}/images/{row['id']}?thumb=1"

    return data


def _searchable_columns(schema: DatasetSchema) -> List[str]:
    cols = []
    for f in schema.fields:
        if f.type == FieldType.text_list and f.group_members and f.searchable:
            cols.extend(f.group_members)
        elif f.searchable and f.type not in (FieldType.split, FieldType.image, FieldType.blob):
            cols.append(f.name)
    return cols


def _list_db_columns(schema: DatasetSchema) -> List[str]:
    cols = ["samples.id", "samples.split"]
    for f in schema.fields:
        if f.type == FieldType.split:
            continue
        if f.type == FieldType.text_list and f.group_members:
            cols.extend(f"samples.{m}" for m in f.group_members)
        elif f.type == FieldType.image:
            cols.append(f"samples.{f.name}")
            cols.extend(["samples.width", "samples.height"])
        elif f.type not in (FieldType.blob,):
            cols.append(f"samples.{f.name}")
    seen: set[str] = set()
    return [c for c in cols if not (c in seen or seen.add(c))]


# --- Dataset registry routes ---


@app.get("/api/datasets", response_model=List[DatasetSummary])
def list_datasets() -> List[DatasetSummary]:
    return list_summaries()


@app.post("/api/datasets", response_model=CreateDatasetResponse)
def create_dataset(req: CreateDatasetRequest) -> CreateDatasetResponse:
    try:
        dataset_id = start_download(req.url)
        schema = load_schema(dataset_id)
        return CreateDatasetResponse(id=dataset_id, status=schema.download.status)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: str) -> DatasetSchema:
    try:
        return load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")


@app.put("/api/datasets/{dataset_id}")
def update_dataset(dataset_id: str, req: UpdateDatasetRequest) -> DatasetSchema:
    try:
        schema = load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    if req.name is not None:
        schema.name = req.name
    if req.fields is not None:
        schema.fields = req.fields
    save_schema(schema)
    return schema


@app.delete("/api/datasets/{dataset_id}")
def remove_dataset(dataset_id: str) -> dict:
    try:
        delete_dataset(dataset_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(404, "Dataset not found")


@app.get("/api/datasets/{dataset_id}/download-status")
def download_status(dataset_id: str) -> dict:
    try:
        schema = load_schema(dataset_id)
        return schema.download.model_dump()
    except KeyError:
        raise HTTPException(404, "Dataset not found")


@app.post("/api/datasets/{dataset_id}/ingest")
def trigger_ingest(dataset_id: str, force: bool = Query(False)) -> dict:
    try:
        load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    try:
        count = ingest_dataset(dataset_id, force=force)
        return {"status": "done", "row_count": count}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/datasets/{dataset_id}/schema/reparse", response_model=ReparseResponse)
def reparse_schema(dataset_id: str) -> ReparseResponse:
    try:
        schema = load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    dest = source_dir(dataset_id)
    readme_path = None
    for candidate in ("README.md", "readme.md", "Readme.md"):
        p = os.path.join(dest, candidate)
        if os.path.exists(p):
            readme_path = p
            break
    if not readme_path:
        raise HTTPException(400, "No README.md found for this dataset")
    with open(readme_path, encoding="utf-8") as f:
        fields, warnings = parse_readme(f.read())
    return ReparseResponse(fields=fields, warnings=warnings)


@app.get("/api/active-dataset", response_model=ActiveDatasetResponse)
def get_active() -> ActiveDatasetResponse:
    return ActiveDatasetResponse(id=get_active_dataset_id())


@app.put("/api/active-dataset", response_model=ActiveDatasetResponse)
def set_active(body: ActiveDatasetResponse) -> ActiveDatasetResponse:
    if body.id is None:
        raise HTTPException(400, "id is required")
    try:
        set_active_dataset_id(body.id)
        return ActiveDatasetResponse(id=body.id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")


# --- Dataset-scoped data routes ---


@app.get("/api/datasets/{dataset_id}/stats", response_model=Stats)
def stats(dataset_id: str) -> Stats:
    try:
        load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    conn = get_connection(dataset_id)
    try:
        total = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        rows = conn.execute(
            "SELECT split, COUNT(*) c FROM samples GROUP BY split"
        ).fetchall()
        splits = {r["split"]: r["c"] for r in rows}
        return Stats(total=total, splits=splits)
    except sqlite3.Error as e:
        raise HTTPException(400, str(e))
    finally:
        conn.close()


@app.get("/api/datasets/{dataset_id}/samples", response_model=SamplesPage)
def list_samples(
    dataset_id: str,
    split: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
) -> SamplesPage:
    try:
        schema = load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")

    conn = get_connection(dataset_id)
    try:
        params: list = []
        where = []
        joins = ""

        fts_query = _fts_query(search) if search else None
        if fts_query:
            joins = "JOIN samples_fts ON samples_fts.rowid = samples.id"
            where.append("samples_fts MATCH ?")
            params.append(fts_query)
        if split:
            where.append("samples.split = ?")
            params.append(split)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        total = conn.execute(
            f"SELECT COUNT(*) FROM samples {joins} {where_sql}", params
        ).fetchone()[0]

        cols = ", ".join(_list_db_columns(schema))
        rows = conn.execute(
            f"SELECT {cols} FROM samples {joins} {where_sql} "
            f"ORDER BY samples.id LIMIT ? OFFSET ?",
            params + [page_size, page * page_size],
        ).fetchall()

        return SamplesPage(
            total=total,
            page=page,
            page_size=page_size,
            rows=[_row_to_dict(r, schema, dataset_id) for r in rows],
        )
    except sqlite3.Error as e:
        raise HTTPException(400, str(e))
    finally:
        conn.close()


@app.get("/api/datasets/{dataset_id}/samples/{sample_id}")
def get_sample(dataset_id: str, sample_id: int) -> Dict[str, Any]:
    try:
        schema = load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    conn = get_connection(dataset_id)
    try:
        row = conn.execute(
            "SELECT * FROM samples WHERE id = ?", (sample_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Sample not found")
        return _row_to_dict(row, schema, dataset_id)
    finally:
        conn.close()


@app.get("/api/datasets/{dataset_id}/images/{sample_id}")
def get_image(dataset_id: str, sample_id: int, thumb: int = 0) -> Response:
    try:
        schema = load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    image_field = _has_image_field(schema)
    if not image_field:
        raise HTTPException(404, "No image field in schema")

    conn = get_connection(dataset_id)
    try:
        col = "thumbnail" if thumb else image_field
        row = conn.execute(
            f"SELECT {col} AS data FROM samples WHERE id = ?", (sample_id,)
        ).fetchone()
        if row is None or row["data"] is None:
            raise HTTPException(404, "Image not found")
        return Response(
            content=bytes(row["data"]),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    finally:
        conn.close()


@app.post("/api/datasets/{dataset_id}/sql", response_model=SqlResponse)
def run_sql(dataset_id: str, req: SqlRequest) -> SqlResponse:
    query = req.query.strip().rstrip(";").strip()
    if not query:
        raise HTTPException(400, "Empty query")
    lowered = query.lower()
    if not lowered.startswith(("select", "with")):
        raise HTTPException(400, "Only SELECT queries are allowed")
    if ";" in query:
        raise HTTPException(400, "Only a single statement is allowed")

    conn = get_readonly_connection(dataset_id)
    try:
        cur = conn.execute(query)
        columns = [d[0] for d in cur.description] if cur.description else []
        out_rows = []
        for r in cur.fetchmany(MAX_SQL_ROWS):
            row = []
            for v in r:
                if isinstance(v, (bytes, bytearray)):
                    row.append(f"<blob {len(v)} bytes>")
                else:
                    row.append(v)
            out_rows.append(row)
        return SqlResponse(columns=columns, rows=out_rows, row_count=len(out_rows))
    except sqlite3.Error as e:
        raise HTTPException(400, f"SQL error: {e}")
    finally:
        conn.close()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
