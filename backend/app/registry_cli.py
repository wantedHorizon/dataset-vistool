"""CLI for dataset registry management."""
import sys

from app.services.registry import drop_all_data, list_dataset_ids


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.registry_cli <drop|list>")
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
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
