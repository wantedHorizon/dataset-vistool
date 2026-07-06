"""FastAPI backend for the dataset visualization tool.

The row schema is metadata-driven: fields.json (repo root) declares the
dataset's logical fields, and this module builds its queries and response
shapes from that metadata (see app/fields.py). GET /api/fields exposes the
same metadata to the frontend.
"""
import re
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .db import get_connection, get_readonly_connection
from .fields import all_columns, load_dataset, load_fields, name_field, searchable_columns
from .ingest import ingest
from .schemas import (
    DatasetMeta,
    FieldMeta,
    FieldsResponse,
    Sample,
    SamplesPage,
    SqlRequest,
    SqlResponse,
    Stats,
)

app = FastAPI(title=f"{load_dataset().title} Visualization API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_SQL_ROWS = 500


@app.on_event("startup")
def _startup() -> None:
    # Build the SQLite DB from parquet on first boot; no-op if already present.
    ingest()


def _row_to_sample(row: sqlite3.Row) -> Sample:
    values = {}
    for f in load_fields():
        if f.type == "string_list":
            values[f.key] = [row[c] for c in f.columns if row[c] is not None]
        else:
            values[f.key] = row[f.columns[0]]
    nf = name_field()
    name = (values.get(nf.key) if nf else None) or f"sample_{row['id']}"
    return Sample(
        id=row["id"],
        name=name,
        fields=values,
        image_url=f"/api/images/{row['id']}",
        thumb_url=f"/api/images/{row['id']}?thumb=1",
    )


def _fts_query(search: str) -> Optional[str]:
    """Turn free text into a safe FTS5 prefix query (AND of quoted tokens)."""
    tokens = re.findall(r"\w+", search)
    if not tokens:
        return None
    return " AND ".join(f'"{t}"*' for t in tokens)


@app.get("/api/fields", response_model=FieldsResponse)
def fields_meta() -> FieldsResponse:
    ds = load_dataset()
    return FieldsResponse(
        dataset=DatasetMeta(name=ds.name, title=ds.title),
        fields=[
            FieldMeta(
                key=f.key,
                label=f.label,
                type=f.type,
                role=f.role,
                visible=f.visible,
                searchable=f.searchable,
                item_count=len(f.columns) if f.type == "string_list" else None,
            )
            for f in load_fields()
        ],
    )


@app.get("/api/stats", response_model=Stats)
def stats() -> Stats:
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        rows = conn.execute(
            "SELECT split, COUNT(*) c FROM samples GROUP BY split"
        ).fetchall()
        splits = {r["split"]: r["c"] for r in rows}
        return Stats(total=total, splits=splits)
    finally:
        conn.close()


@app.get("/api/samples", response_model=SamplesPage)
def list_samples(
    split: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
) -> SamplesPage:
    conn = get_connection()
    try:
        if split is not None:
            valid_splits = {
                r[0] for r in conn.execute("SELECT DISTINCT split FROM samples")
            }
            if split not in valid_splits:
                raise HTTPException(400, f"Invalid split '{split}'")

        params: list = []
        where = []
        joins = ""

        fts_query = _fts_query(search) if search else None
        if fts_query:
            if not searchable_columns():
                raise HTTPException(400, "No searchable fields configured")
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

        cols = ", ".join(["samples.id"] + [f"samples.{c}" for c in all_columns()])
        rows = conn.execute(
            f"SELECT {cols} FROM samples {joins} {where_sql} "
            f"ORDER BY samples.id LIMIT ? OFFSET ?",
            params + [page_size, page * page_size],
        ).fetchall()

        return SamplesPage(
            total=total,
            page=page,
            page_size=page_size,
            rows=[_row_to_sample(r) for r in rows],
        )
    finally:
        conn.close()


@app.get("/api/samples/{sample_id}", response_model=Sample)
def get_sample(sample_id: int) -> Sample:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM samples WHERE id = ?", (sample_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Sample not found")
        return _row_to_sample(row)
    finally:
        conn.close()


@app.get("/api/images/{sample_id}")
def get_image(sample_id: int, thumb: int = 0) -> Response:
    conn = get_connection()
    try:
        col = "thumbnail" if thumb else "image"
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


@app.post("/api/sql", response_model=SqlResponse)
def run_sql(req: SqlRequest) -> SqlResponse:
    """Run a single read-only SELECT. BLOB columns are redacted."""
    query = req.query.strip().rstrip(";").strip()
    if not query:
        raise HTTPException(400, "Empty query")
    lowered = query.lower()
    if not lowered.startswith(("select", "with")):
        raise HTTPException(400, "Only SELECT queries are allowed")
    if ";" in query:
        raise HTTPException(400, "Only a single statement is allowed")

    conn = get_readonly_connection()
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
