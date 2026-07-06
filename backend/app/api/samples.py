"""Sample browsing and image routes."""
import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Response

from app.db.columns import select_columns
from app.db.connection import get_connection
from app.models.api import SamplesPage, Stats
from app.services.query import build_samples_where, has_image_field, row_to_dict
from app.services.registry import load_schema

router = APIRouter()


@router.get("/api/datasets/{dataset_id}/stats", response_model=Stats)
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


@router.get("/api/datasets/{dataset_id}/samples", response_model=SamplesPage)
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
        joins, where_sql, params = build_samples_where(search, split)

        total = conn.execute(
            f"SELECT COUNT(*) FROM samples {joins} {where_sql}", params
        ).fetchone()[0]

        cols = ", ".join(select_columns(schema))
        rows = conn.execute(
            f"SELECT {cols} FROM samples {joins} {where_sql} "
            f"ORDER BY samples.id LIMIT ? OFFSET ?",
            params + [page_size, page * page_size],
        ).fetchall()

        return SamplesPage(
            total=total,
            page=page,
            page_size=page_size,
            rows=[row_to_dict(r, schema, dataset_id) for r in rows],
        )
    except sqlite3.Error as e:
        raise HTTPException(400, str(e))
    finally:
        conn.close()


@router.get("/api/datasets/{dataset_id}/samples/{sample_id}")
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
        return row_to_dict(row, schema, dataset_id)
    finally:
        conn.close()


@router.get("/api/datasets/{dataset_id}/images/{sample_id}")
def get_image(dataset_id: str, sample_id: int, thumb: int = 0) -> Response:
    try:
        schema = load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    image_field = has_image_field(schema)
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
