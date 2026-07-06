"""Pydantic response/request models."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Sample(BaseModel):
    id: int
    # Display name (the role="name" field, or a fallback), computed server-side
    # so the frontend never needs to know which field key is the name.
    name: str
    # All logical field values, keyed by fields.json field key.
    fields: Dict[str, Any]
    image_url: str
    thumb_url: str


class SamplesPage(BaseModel):
    total: int
    page: int
    page_size: int
    rows: List[Sample]


class DatasetMeta(BaseModel):
    name: str
    title: str


class FieldMeta(BaseModel):
    key: str
    label: str
    type: str
    role: Optional[str] = None
    visible: bool
    searchable: bool
    # Number of items in a string_list field (None for scalar fields), so the
    # frontend can fan a list field out into per-item table columns.
    item_count: Optional[int] = None


class FieldsResponse(BaseModel):
    dataset: DatasetMeta
    fields: List[FieldMeta]


class Stats(BaseModel):
    total: int
    splits: dict


class SqlRequest(BaseModel):
    query: str


class SqlResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
