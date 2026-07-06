"""CLI for dataset registry management."""
import sys

from app.services.ingest import ingest_all_pending
from app.services.registry import drop_all_data, init_registry, list_dataset_ids


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.registry_cli <drop|list|populate> [--force]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "drop":
        drop_all_data()
        print("[registry] All dataset data removed.")
    elif cmd == "list":
        ids = list_dataset_ids()
        if not ids:
            print("(no datasets registered)")
        for did in ids:
            print(did)
    elif cmd == "populate":
        force = "--force" in sys.argv[2:]
        init_registry()
        ingest_all_pending(force=force)
        print("[registry] Populate complete.")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
