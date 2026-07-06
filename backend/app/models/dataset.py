"""Domain configuration models for per-dataset schema."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    text = "text"
    text_list = "text_list"
    image = "image"
    integer = "integer"
    split = "split"
    blob = "blob"


class FieldDef(BaseModel):
    name: str
    source: str
    type: FieldType = FieldType.text
    visible: bool = True
    searchable: bool = False
    group_members: Optional[List[str]] = None


class SplitConfig(BaseModel):
    strategy: str = "filename_prefix"
    column: Optional[str] = None
    values: Optional[List[str]] = None


class SourceConfig(BaseModel):
    type: str = "parquet"
    path: str
    split: SplitConfig = Field(default_factory=SplitConfig)


class JobStatus(BaseModel):
    status: str = "idle"
    message: Optional[str] = None
    row_count: int = 0


class DownloadStatus(BaseModel):
    status: str = "idle"
    progress: Optional[str] = None
    message: Optional[str] = None
    phase: Optional[str] = None
    schema_source: Optional[str] = None
    field_count: int = 0
    bytes_total: Optional[int] = None
    parquet_files_total: int = 0
    parquet_files_done: int = 0


class DatasetSchema(BaseModel):
    id: str
    name: str
    source_url: Optional[str] = None
    source: SourceConfig
    fields: List[FieldDef] = Field(default_factory=list)
    ingest: JobStatus = Field(default_factory=JobStatus)
    download: DownloadStatus = Field(default_factory=DownloadStatus)
