"""SQL console route."""
import sqlite3

from fastapi import APIRouter, HTTPException

from app.config import MAX_SQL_ROWS
from app.db.connection import get_readonly_connection
from app.models.api import SqlRequest, SqlResponse
from app.services.registry import load_schema

router = APIRouter()


@router.post("/api/datasets/{dataset_id}/sql", response_model=SqlResponse)
def run_sql(dataset_id: str, req: SqlRequest) -> SqlResponse:
    try:
        load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")

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
