"""Central configuration and path constants."""
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(APP_DIR)

DATA_ROOT = os.path.abspath(
    os.environ.get("DATA_ROOT", os.path.join(BACKEND_DIR, "data"))
)
REGISTRY_PATH = os.path.join(DATA_ROOT, "registry.json")
DATASETS_DIR = os.path.join(DATA_ROOT, "datasets")

LEGACY_DB_PATH = os.path.abspath(
    os.environ.get(
        "DB_PATH",
        os.path.join(DATA_ROOT, "flickr8k.db"),
    )
)
LEGACY_PARQUET_DIR = os.path.abspath(
    os.environ.get(
        "PARQUET_DIR",
        os.path.join(BACKEND_DIR, "..", "datasets", "jxie-flickr8k", "data"),
    )
)

MAX_SQL_ROWS = 500
