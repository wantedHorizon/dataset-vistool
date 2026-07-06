"""Sample query building and row serialization."""
import re
import sqlite3
from typing import Any, Dict, List, Optional

from app.models.dataset import DatasetSchema, FieldType


def fts_query(search: str) -> Optional[str]:
    tokens = re.findall(r"\w+", search)
    if not tokens:
        return None
    return " AND ".join(f'"{t}"*' for t in tokens)


def has_image_field(schema: DatasetSchema) -> Optional[str]:
    for f in schema.fields:
        if f.type == FieldType.image:
            return f.name
    return None


def row_to_dict(row: sqlite3.Row, schema: DatasetSchema, dataset_id: str) -> Dict[str, Any]:
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

    image_field = has_image_field(schema)
    if image_field and image_field in keys and row[image_field] is not None:
        data["image_url"] = f"/api/datasets/{dataset_id}/images/{row['id']}"
        data["thumb_url"] = f"/api/datasets/{dataset_id}/images/{row['id']}?thumb=1"

    return data


def build_samples_where(
    search: Optional[str], split: Optional[str]
) -> tuple[str, str, list]:
    """Return (joins, where_sql, params) for a samples list query."""
    params: list = []
    where = []
    joins = ""

    fts = fts_query(search) if search else None
    if fts:
        joins = "JOIN samples_fts ON samples_fts.rowid = samples.id"
        where.append("samples_fts MATCH ?")
        params.append(fts)
    if split:
        where.append("samples.split = ?")
        params.append(split)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    return joins, where_sql, params
