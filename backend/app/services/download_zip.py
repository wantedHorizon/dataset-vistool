"""Resolve sample selection and stream a ZIP of images + metadata.jsonl."""
from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import zipfile
from typing import Iterator, List, Optional, Tuple

from fastapi import HTTPException

from app.config import MAX_DOWNLOAD_ROWS
from app.db.columns import select_columns
from app.db.connection import get_connection
from app.models.api import DownloadMode, DownloadRequest
from app.services.query import build_samples_where, has_image_field, row_to_dict
from app.services.registry import load_schema

_FETCH_BATCH = 50


def _append_clause(where_sql: str, clause: str) -> str:
    if where_sql:
        return f"{where_sql} AND {clause}"
    return f"WHERE {clause}"


def _id_list_clause(
    column: str, ids: List[int], params: list, *, negate: bool = False
) -> str:
    """Bind id lists via json_each to stay under SQLite parameter limits."""
    params.append(json.dumps(ids))
    op = "NOT IN" if negate else "IN"
    return f"{column} {op} (SELECT value FROM json_each(?))"


def _build_selection(
    req: DownloadRequest,
) -> Tuple[str, str, list, Optional[int], Optional[int]]:
    """Return (joins, where_sql, params, limit, offset) before exclude_ids."""
    joins, where_sql, params = build_samples_where(req.search, req.split)

    if req.mode == DownloadMode.ids:
        assert req.ids is not None
        where_sql = _append_clause(
            where_sql, _id_list_clause("samples.id", req.ids, params)
        )
        return joins, where_sql, params, None, None

    if req.mode == DownloadMode.range:
        return joins, where_sql, params, req.limit, req.offset

    # mode == all: filter only, no window
    return joins, where_sql, params, None, None


def _count_rows(
    conn: sqlite3.Connection,
    joins: str,
    where_sql: str,
    params: list,
    limit: Optional[int],
    offset: Optional[int],
) -> int:
    if limit is not None:
        inner = (
            f"SELECT samples.id FROM samples {joins} {where_sql} "
            f"ORDER BY samples.id LIMIT ? OFFSET ?"
        )
        row = conn.execute(
            f"SELECT COUNT(*) FROM ({inner})",
            params + [limit, offset or 0],
        ).fetchone()
        return int(row[0])

    row = conn.execute(
        f"SELECT COUNT(*) FROM samples {joins} {where_sql}", params
    ).fetchone()
    return int(row[0])


def build_download_zip(dataset_id: str, req: DownloadRequest) -> Iterator[bytes]:
    """Validate selection, build a ZIP on a spooled temp file, yield chunks."""
    try:
        schema = load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")

    if req.mode == DownloadMode.range and req.limit is not None:
        if req.limit > MAX_DOWNLOAD_ROWS:
            raise HTTPException(
                413,
                f"Requested limit {req.limit} exceeds max of {MAX_DOWNLOAD_ROWS} rows",
            )

    joins, where_sql, params, limit, offset = _build_selection(req)

    conn = get_connection(dataset_id)
    try:
        count = _count_rows(conn, joins, where_sql, params, limit, offset)
        if count == 0:
            raise HTTPException(400, "No samples matched the selection")
        if count > MAX_DOWNLOAD_ROWS:
            raise HTTPException(
                413,
                f"Selection has {count} rows; max is {MAX_DOWNLOAD_ROWS}",
            )

        fetch_where = where_sql
        fetch_params = list(params)
        if req.mode in (DownloadMode.all, DownloadMode.range) and req.exclude_ids:
            fetch_where = _append_clause(
                fetch_where,
                _id_list_clause(
                    "samples.id", req.exclude_ids, fetch_params, negate=True
                ),
            )

        cols = ", ".join(select_columns(schema))
        sql = (
            f"SELECT {cols} FROM samples {joins} {fetch_where} "
            f"ORDER BY samples.id"
        )
        sql_params = fetch_params
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            sql_params = fetch_params + [limit, offset or 0]

        image_field = has_image_field(schema)
        spool = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
        wrote_any = False

        with zipfile.ZipFile(spool, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            meta_buf = io.StringIO()
            cur = conn.execute(sql, sql_params)
            while True:
                rows = cur.fetchmany(_FETCH_BATCH)
                if not rows:
                    break
                for row in rows:
                    wrote_any = True
                    record = row_to_dict(row, schema, dataset_id)
                    if (
                        image_field
                        and image_field in row.keys()
                        and row[image_field] is not None
                    ):
                        image_path = f"images/{row['id']}.jpg"
                        zf.writestr(image_path, bytes(row[image_field]))
                        record["image_file"] = image_path
                    meta_buf.write(json.dumps(record, separators=(",", ":")) + "\n")
            zf.writestr("metadata.jsonl", meta_buf.getvalue())

        if not wrote_any:
            spool.close()
            raise HTTPException(400, "No samples matched the selection")

        spool.seek(0)

        def iter_chunks() -> Iterator[bytes]:
            try:
                while True:
                    chunk = spool.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk
            finally:
                spool.close()
                conn.close()

        return iter_chunks()
    except HTTPException:
        conn.close()
        raise
    except sqlite3.Error as e:
        conn.close()
        raise HTTPException(400, str(e)) from e
