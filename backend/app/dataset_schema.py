"""Pydantic models for per-dataset schema configuration."""
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
    # For text_list: member field names grouped under one column
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


class DatasetSchema(BaseModel):
    id: str
    name: str
    source_url: Optional[str] = None
    source: SourceConfig
    fields: List[FieldDef] = Field(default_factory=list)
    ingest: JobStatus = Field(default_factory=JobStatus)
    download: DownloadStatus = Field(default_factory=DownloadStatus)


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
