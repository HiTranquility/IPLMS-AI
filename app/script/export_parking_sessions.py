"""Export changed operational sessions into the local data-lake workspace."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import get_config
from app.infra.datalake import SessionExporter


def main() -> int:
    config = get_config().datalake
    parser = argparse.ArgumentParser(description="Export PostgreSQL parking sessions to data lake")
    parser.add_argument("--output", type=Path, default=Path(config.local_path))
    parser.add_argument(
        "--database-url",
        help=(
            "Operational PostgreSQL URL; prefer AI_DATALAKE_SOURCE_DATABASE_URL "
            "so credentials do not appear in shell history"
        ),
    )
    parser.add_argument("--since", help="ISO-8601 lower watermark (exclusive)")
    parser.add_argument("--until", help="ISO-8601 upper watermark (inclusive)")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print the configured destination without connecting to PostgreSQL",
    )
    args = parser.parse_args()

    if args.status:
        print(
            json.dumps(
                {
                    "dataset": "parking_sessions",
                    "format": "jsonl+manifest",
                    "output": str(args.output),
                    "batch_size": config.export_batch_size,
                    "source_database_configured": bool(
                        args.database_url or config.source_database_url
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 0

    result = SessionExporter(
        db_url=args.database_url,
        root_path=args.output,
    ).export(
        since=args.since,
        until=args.until,
    )
    print(
        json.dumps(
            {
                "data_file": str(result.data_file),
                "manifest_file": str(result.manifest_file),
                "record_count": result.record_count,
                "sha256": result.sha256,
                "watermark": result.watermark.isoformat(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
