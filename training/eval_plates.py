"""Máy đo độ chính xác ANPR trên bộ vàng (SUGGESTION-007 · B1).

Chạy engine đọc biển hiện tại trên từng ảnh trong `data/golden/plates/manifest.json`,
so với nhãn người gán, rồi in bảng số và ghi báo cáo JSON.

```bash
cd ai
python training/eval_plates.py                        # chạy cả bộ vàng
python training/eval_plates.py --limit 20             # thử nhanh
python training/eval_plates.py --tag night            # chỉ ảnh ban đêm
python training/eval_plates.py --label before-B2      # đặt tên báo cáo
```

**[MUST] Mọi PR đụng model / pipeline nhận diện phải kèm số TRƯỚC và SAU trên
cùng bộ vàng này.** Không có số thì không biết thay đổi đó làm tốt lên hay tệ đi,
và mọi lần tinh chỉnh sau sẽ là cảm tính.

Đo **engine** (`anpr_engine.run_anpr`) chứ không đo `AnprService`: service còn
kèm tầng phân loại xe và việc ghi ảnh xuống đĩa — những thứ không thuộc câu hỏi
"đọc biển đúng bao nhiêu phần trăm".
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Console Windows mặc định không phải UTF-8 (cp932/cp1258 tuỳ máy), và bảng số
# dưới đây có dấu tiếng Việt — không ép encoding thì script chết bằng
# UnicodeEncodeError ngay dòng print đầu tiên, trước cả khi đo được gì.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Cho phép `python training/eval_plates.py` chạy từ thư mục `ai/`.
AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from training.plate_metrics import aggregate, group_by_tag, score_one  # noqa: E402

DEFAULT_GOLDEN_DIR = AI_ROOT / "data" / "golden" / "plates"


def display_path(path: Path) -> str:
    """Đường dẫn gọn khi nằm trong `ai/`, đường dẫn đầy đủ khi ở ngoài.

    `--golden-dir` trỏ ra ngoài `ai/` là hợp lệ, nên `relative_to` phải có nhánh
    dự phòng thay vì ném ValueError đúng lúc đã đo xong và chỉ còn việc in ra.
    """
    try:
        return str(path.relative_to(AI_ROOT))
    except ValueError:
        return str(path)


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    if not manifest_path.exists():
        raise SystemExit(
            f"Không thấy manifest: {manifest_path}\n"
            f"Dựng bộ vàng trước — xem {DEFAULT_GOLDEN_DIR / 'README.md'}"
        )
    with manifest_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def run_one(image_path: Path) -> Dict[str, Any]:
    """Chạy ANPR trên một ảnh. Lỗi được GHI LẠI chứ không làm sập cả lượt đo.

    Một ảnh không đọc được là một điểm dữ liệu ("engine bó tay ở ca này"), không
    phải lý do để bỏ dở 200 ảnh còn lại.
    """
    from app.core.exceptions import InvalidImageError, PlateRecognitionError
    from app.core.vision.engines.anpr_engine import run_anpr

    try:
        started = time.time()
        result = run_anpr(image_path.read_bytes())
        return {
            "predicted": result.get("plate_number"),
            "confidence": result.get("confidence"),
            "process_time": result.get("process_time", round(time.time() - started, 3)),
            "error": None,
        }
    except (PlateRecognitionError, InvalidImageError) as exc:
        return {
            "predicted": None,
            "confidence": 0.0,
            "process_time": None,
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001 — lỗi lạ vẫn phải thành một dòng số liệu
        return {
            "predicted": None,
            "confidence": 0.0,
            "process_time": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def evaluate(items: List[Dict[str, Any]], images_dir: Path) -> List[Dict[str, Any]]:
    from app.core.constants import FALLBACK_PLATE_NUMBER

    rows: List[Dict[str, Any]] = []
    total = len(items)
    for idx, item in enumerate(items, start=1):
        image_path = images_dir / str(item["file"])
        if not image_path.exists():
            rows.append(
                {
                    **score_one(item["plate"], None),
                    "file": item["file"],
                    "tags": item.get("tags") or [],
                    "confidence": None,
                    "process_time": None,
                    "error": "ảnh không tồn tại",
                }
            )
            continue

        outcome = run_one(image_path)
        predicted = outcome["predicted"]
        # `UNKNOWN` là engine tự thừa nhận không đọc được — chấm như không đọc ra
        # gì, chứ không phải một chuỗi đoán sai.
        if predicted == FALLBACK_PLATE_NUMBER:
            predicted = None

        rows.append(
            {
                **score_one(item["plate"], predicted),
                "file": item["file"],
                "tags": item.get("tags") or [],
                "confidence": outcome["confidence"],
                "process_time": outcome["process_time"],
                "error": outcome["error"],
            }
        )
        label = item["plate"]
        print(f"  [{idx}/{total}] {item['file']:<28} {label:<12} -> {predicted or '—'}")
    return rows


def _pct(value: float) -> str:
    return f"{float(value) * 100:5.1f}%"


def print_table(summary: Dict[str, Any], by_tag: Dict[str, Dict[str, Any]]) -> None:
    print("\n" + "=" * 62)
    print("  KẾT QUẢ ĐO TRÊN BỘ VÀNG")
    print("=" * 62)
    print(f"  Số ảnh                : {summary['total']}")
    print(
        f"  Đọc ra được biển      : {summary['recognized']}"
        f"  ({_pct(summary['recognition_rate'])})"
    )
    print(
        f"  Exact match (strict)  : {_pct(summary['exact_match_strict'])}"
        "   <- có cả gạch/chấm"
    )
    print(
        f"  Exact match (relaxed) : {_pct(summary['exact_match_relaxed'])}"
        "   <- bỏ dấu phân cách"
    )
    print(f"  CER trung bình        : {summary['mean_cer']:.4f}")
    print(f"  CER trung vị          : {summary['median_cer']:.4f}")
    print(f"  Confidence trung bình : {summary['mean_confidence']:.4f}")
    print(f"  Lỗi khi chạy          : {summary['errors']}")
    print(
        f"  Latency p50 / p95     : {summary['latency_p50']:.3f}s"
        f" / {summary['latency_p95']:.3f}s"
    )

    gap = summary["exact_match_relaxed"] - summary["exact_match_strict"]
    if gap > 0:
        print(
            f"\n  [!] Chênh strict/relaxed: {_pct(gap)} số ảnh đọc ĐÚNG ký tự nhưng"
            "\n      sai dấu phân cách. Đây đúng là phần B2 (hậu xử lý biển VN)"
            "\n      lấy về được mà không cần đổi model."
        )

    if by_tag:
        print("\n  Tách theo điều kiện ảnh:")
        print(f"    {'tag':<12} {'n':>4}  {'strict':>7} {'relaxed':>8} {'CER':>7}")
        for tag, stats in by_tag.items():
            print(
                f"    {tag:<12} {stats['total']:>4}  {_pct(stats['exact_match_strict']):>7}"
                f" {_pct(stats['exact_match_relaxed']):>8} {stats['mean_cer']:>7.4f}"
            )
    print("=" * 62)


def main() -> int:
    parser = argparse.ArgumentParser(description="Đo độ chính xác ANPR trên bộ vàng")
    parser.add_argument("--golden-dir", type=Path, default=DEFAULT_GOLDEN_DIR)
    parser.add_argument(
        "--manifest", type=Path, default=None, help="mặc định <golden-dir>/manifest.json"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="chỉ chạy N ảnh đầu (0 = tất cả)"
    )
    parser.add_argument(
        "--tag", action="append", default=[], help="chỉ ảnh có tag này (lặp lại được)"
    )
    parser.add_argument(
        "--label", default="", help="nhãn gắn vào tên file báo cáo, vd `before-B2`"
    )
    parser.add_argument("--no-report", action="store_true", help="chỉ in, không ghi file")
    args = parser.parse_args()

    manifest_path = args.manifest or (args.golden_dir / "manifest.json")
    manifest = load_manifest(manifest_path)
    images_dir = args.golden_dir / manifest.get("images_dir", "images")

    items = manifest.get("items") or []
    if args.tag:
        wanted = set(args.tag)
        items = [i for i in items if wanted & set(i.get("tags") or [])]
    if args.limit:
        items = items[: args.limit]

    if not items:
        print(
            f"Bộ vàng rỗng (manifest: {manifest_path}).\n"
            "Nạp ảnh vào trước: python training/import_plate_dataset.py --help\n"
            f"Hướng dẫn đầy đủ: {args.golden_dir / 'README.md'}"
        )
        return 1

    print(f"Đo {len(items)} ảnh từ {images_dir} ...")
    print("(lượt đầu mất ~20s để nạp EasyOCR + YOLO)\n")

    rows = evaluate(items, images_dir)
    summary = aggregate(rows)
    by_tag = group_by_tag(rows)
    print_table(summary, by_tag)

    if args.no_report:
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"-{args.label}" if args.label else ""
    report_path = args.golden_dir / "reports" / f"{stamp}{suffix}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "run_at": datetime.now(timezone.utc).isoformat(),
                "label": args.label,
                "manifest_version": manifest.get("version"),
                "yolo_model": manifest.get(
                    "yolo_model", "model/artifacts/bootstrap/anpr/best.pt"
                ),
                "summary": summary,
                "by_tag": by_tag,
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nBáo cáo: {display_path(report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
