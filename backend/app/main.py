"""FastAPI app factory — middleware, lifespan, router mounting."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import datasets, samples, sql
from app.db.connection import ensure_registry
from app.services.ingest import ingest_all_pending


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_registry()
    ingest_all_pending()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Dataset Explorer API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(datasets.router)
    app.include_router(samples.router)
    app.include_router(sql.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
