"""API request/response DTOs."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .dataset import FieldDef


class DatasetSummary(BaseModel):
    id: str
    name: str
    source_url: Optional[str] = None
    download_status: str
    ingest_status: str
    row_count: int = 0


class CreateDatasetRequest(BaseModel):
    url: str


class CreateDatasetResponse(BaseModel):
    id: str
    status: str


class UpdateDatasetRequest(BaseModel):
    name: Optional[str] = None
    fields: Optional[List[FieldDef]] = None


class SamplesPage(BaseModel):
    total: int
    page: int
    page_size: int
    rows: List[Dict[str, Any]]


class Stats(BaseModel):
    total: int
    splits: dict


class SqlRequest(BaseModel):
    query: str


class SqlResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int


class ActiveDatasetResponse(BaseModel):
    id: Optional[str]


class ReparseResponse(BaseModel):
    fields: List[FieldDef]
    warnings: List[str]
    schema_source: Optional[str] = None
