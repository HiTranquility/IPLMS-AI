"""CLI for evaluating occupancy forecasting baselines on exported sessions."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.infra.datalake.occupancy_reader import OccupancyReader
from training.forecast.baselines import backtest_baselines
from training.forecast.dataset import discover_lot_ids, regularize_history
from training.forecast.snapshot import load_snapshot


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        horizons = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("horizons must be comma-separated integers") from exc
    if not horizons or any(item <= 0 for item in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive")
    return horizons


def _render_table(summary: list[dict[str, Any]]) -> str:
    if not summary:
        return "No evaluable observations were found."
    lines = [
        "model           lot                         horizon  count       MAE      RMSE",
        "--------------- --------------------------- ------- ------ --------- ---------",
    ]
    for row in summary:
        lines.append(
            f"{row['model']:<15} {row['parking_lot_id']:<27} "
            f"{row['horizon_slots']:>7} {row['count']:>6} "
            f"{row['mae']:>9.4f} {row['rmse']:>9.4f}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backtest persistence and weekly seasonal-naive occupancy baselines."
    )
    parser.add_argument("--data-lake", type=Path, default=Path("data/datalake"))
    parser.add_argument(
        "--snapshot-manifest",
        type=Path,
        help="verified occupancy snapshot; preferred for reproducible reports",
    )
    parser.add_argument("--lot-id", action="append", dest="lot_ids")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--horizons", type=_parse_horizons, default=(1, 2, 4, 8))
    parser.add_argument("--seasonal-period-slots", type=int, default=7 * 24 * 2)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.snapshot_manifest:
        if args.lot_ids:
            parser.error("--lot-id cannot be combined with --snapshot-manifest")
        snapshot, regularized = load_snapshot(args.snapshot_manifest)
        lot_ids = list(snapshot.get("parking_lot_ids") or [])
        observed_count = int(snapshot.get("observed_count", 0))
        source = {"snapshot_id": snapshot.get("snapshot_id")}
    else:
        lot_ids = sorted(set(args.lot_ids or discover_lot_ids(args.data_lake)))
        if not lot_ids:
            parser.error(
                "no parking lot IDs found; export PostgreSQL sessions first or pass --lot-id"
            )

        reader = OccupancyReader(base_path=str(args.data_lake))
        observed: list[dict[str, Any]] = []
        for lot_id in lot_ids:
            observed.extend(reader.load_historical_occupancy(lot_id, days=args.days))
        if not observed:
            parser.error("the exported sessions produced no observed occupancy slots")
        regularized = regularize_history(observed)
        observed_count = len(observed)
        source = {"data_lake": str(args.data_lake.resolve())}
    result = backtest_baselines(
        regularized,
        horizons=args.horizons,
        seasonal_period_slots=args.seasonal_period_slots,
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "lot_ids": lot_ids,
        "days": args.days,
        "horizons": list(args.horizons),
        "seasonal_period_slots": args.seasonal_period_slots,
        "observed_slots": observed_count,
        "regularized_slots": len(regularized),
        **result,
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(_render_table(result["summary"]))
        if args.report:
            print(f"\nReport: {args.report.resolve()}")
    return 0 if result["summary"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
