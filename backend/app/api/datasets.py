"""Dataset registry and management routes."""
from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.models.api import (
    ActiveDatasetResponse,
    CreateDatasetRequest,
    CreateDatasetResponse,
    DatasetSummary,
    ReparseResponse,
    UpdateDatasetRequest,
)
from app.models.dataset import DatasetSchema
from app.services.download import reparse_schema as reparse_dataset_schema, start_download
from app.services.ingest import ingest_dataset
from app.services.registry import (
    delete_dataset,
    get_active_dataset_id,
    list_summaries,
    load_schema,
    save_schema,
    set_active_dataset_id,
)

router = APIRouter()


@router.get("/api/datasets", response_model=List[DatasetSummary])
def list_datasets() -> List[DatasetSummary]:
    return list_summaries()


@router.post("/api/datasets", response_model=CreateDatasetResponse)
def create_dataset(req: CreateDatasetRequest) -> CreateDatasetResponse:
    try:
        dataset_id = start_download(req.url)
        schema = load_schema(dataset_id)
        return CreateDatasetResponse(id=dataset_id, status=schema.download.status)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: str) -> DatasetSchema:
    try:
        return load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")


@router.put("/api/datasets/{dataset_id}")
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


@router.delete("/api/datasets/{dataset_id}")
def remove_dataset(dataset_id: str) -> dict:
    try:
        delete_dataset(dataset_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(404, "Dataset not found")


@router.get("/api/datasets/{dataset_id}/download-status")
def download_status(dataset_id: str) -> dict:
    try:
        schema = load_schema(dataset_id)
        return schema.download.model_dump()
    except KeyError:
        raise HTTPException(404, "Dataset not found")


@router.post("/api/datasets/{dataset_id}/ingest")
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


@router.post("/api/datasets/{dataset_id}/schema/reparse", response_model=ReparseResponse)
def reparse_schema_endpoint(dataset_id: str) -> ReparseResponse:
    try:
        load_schema(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    try:
        fields, warnings, schema_source = reparse_dataset_schema(dataset_id)
        return ReparseResponse(
            fields=fields, warnings=warnings, schema_source=schema_source
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/api/active-dataset", response_model=ActiveDatasetResponse)
def get_active() -> ActiveDatasetResponse:
    return ActiveDatasetResponse(id=get_active_dataset_id())


@router.put("/api/active-dataset", response_model=ActiveDatasetResponse)
def set_active(body: ActiveDatasetResponse) -> ActiveDatasetResponse:
    if body.id is None:
        raise HTTPException(400, "id is required")
    try:
        set_active_dataset_id(body.id)
        return ActiveDatasetResponse(id=body.id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
