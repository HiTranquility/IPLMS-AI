"""Nạp một dataset biển số công khai vào bộ vàng (SUGGESTION-007 · B1).

Dataset ANPR công khai mỗi bộ gói nhãn một kiểu. Script này quy ba kiểu hay gặp
nhất về **một** `manifest.json` để `eval_plates.py` chỉ phải biết một định dạng:

| `--from`   | Dataset trông thế nào | Ví dụ |
|---|---|---|
| `filename` | Biển số nằm trong TÊN FILE | `51F17812.jpg`, `xe_51F-178.12_01.jpg` |
| `sidecar`  | Mỗi ảnh kèm một `.txt` cùng tên chứa biển số | `0001.jpg` + `0001.txt` |
| `csv`      | Một file CSV có cột ảnh + cột biển số | `labels.csv` |

```bash
cd ai
python training/import_plate_dataset.py --from filename --src ~/Downloads/vn-plates
python training/import_plate_dataset.py --from csv --src ~/Downloads/ds --csv labels.csv
python training/import_plate_dataset.py --from sidecar --src ~/Downloads/ds --tags night,blur
```

**Ảnh được COPY vào `data/golden/plates/images/`** chứ không tham chiếu tại chỗ:
bộ vàng phải đứng yên. Dataset gốc nằm trong Downloads sẽ bị dọn, đổi tên, hoặc
tải lại bản khác — lúc đó con số đo hôm nay không còn tái lập được nữa.

**[NEVER] commit ảnh.** `.gitignore` chỉ cho `manifest.json` + `README.md` +
`reports/` vào git; ảnh biển số là PII (ADR-0003 §4).

**[GOTCHA] Dataset công khai KHÔNG thay được ảnh cổng thật.** ADR-0003 §1 đã
chốt: ảnh web khác ảnh camera cổng về góc máy, ánh sáng, độ nhoè. Số đo trên
dataset công khai là **mốc khởi điểm để so tương đối giữa các lần sửa**, không
phải con số sẽ thấy ở cổng thật. Có ảnh phiên đỗ thật thì nạp đè và đo lại.
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Console Windows mặc định không phải UTF-8 — xem ghi chú cùng chỗ ở eval_plates.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

DEFAULT_GOLDEN_DIR = AI_ROOT / "data" / "golden" / "plates"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Nhóm bắt tên `plate` là chỗ biển số nằm trong tên file. Mặc định khớp cả
# `51F17812`, `51F-178.12` và `29A-12345`.
DEFAULT_FILENAME_PATTERN = r"(?P<plate>\d{2}[A-Z]{1,2}\d?-?\d{3}\.?\d{2})"


def display_path(path: Path) -> str:
    """Đường dẫn gọn khi nằm trong `ai/`, đường dẫn đầy đủ khi ở ngoài.

    `--golden-dir` trỏ ra ngoài `ai/` là hợp lệ (so hai bộ vàng, hoặc để bộ vàng
    trên ổ khác), nên `relative_to` phải có nhánh dự phòng thay vì ném ValueError
    đúng lúc mọi việc đã làm xong.
    """
    try:
        return str(path.relative_to(AI_ROOT))
    except ValueError:
        return str(path)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_images(src: Path):
    for path in sorted(src.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            yield path


def collect_from_filename(src: Path, pattern: str) -> List[Tuple[Path, str]]:
    regex = re.compile(pattern, re.IGNORECASE)
    found: List[Tuple[Path, str]] = []
    skipped = 0
    for image in iter_images(src):
        match = regex.search(image.stem.upper())
        if not match:
            skipped += 1
            continue
        found.append((image, match.group("plate")))
    if skipped:
        print(f"  bỏ qua {skipped} ảnh không khớp pattern {pattern!r}")
    return found


def collect_from_sidecar(src: Path) -> List[Tuple[Path, str]]:
    found: List[Tuple[Path, str]] = []
    missing = 0
    for image in iter_images(src):
        sidecar = image.with_suffix(".txt")
        if not sidecar.exists():
            missing += 1
            continue
        plate = sidecar.read_text(encoding="utf-8", errors="ignore").strip()
        if plate:
            found.append((image, plate))
        else:
            missing += 1
    if missing:
        print(f"  bỏ qua {missing} ảnh thiếu .txt hoặc .txt rỗng")
    return found


def collect_from_csv(
    src: Path, csv_path: Path, image_column: str, plate_column: str
) -> List[Tuple[Path, str]]:
    if not csv_path.exists():
        raise SystemExit(f"Không thấy file CSV: {csv_path}")

    found: List[Tuple[Path, str]] = []
    missing = 0
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise SystemExit(f"CSV không có dòng tiêu đề: {csv_path}")
        for column in (image_column, plate_column):
            if column not in reader.fieldnames:
                raise SystemExit(
                    f"CSV thiếu cột {column!r}. Cột đang có: {reader.fieldnames}\n"
                    "Chỉ định bằng --image-column / --plate-column."
                )
        for row in reader:
            raw_name = (row.get(image_column) or "").strip()
            plate = (row.get(plate_column) or "").strip()
            if not raw_name or not plate:
                missing += 1
                continue
            image = (src / raw_name).resolve()
            if not image.exists():
                # CSV hay ghi đường dẫn tương đối từ một gốc khác — thử tìm theo tên.
                candidates = list(src.rglob(Path(raw_name).name))
                if not candidates:
                    missing += 1
                    continue
                image = candidates[0]
            found.append((image, plate))
    if missing:
        print(f"  bỏ qua {missing} dòng CSV thiếu ảnh hoặc thiếu nhãn")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nạp dataset biển số công khai vào bộ vàng",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--from",
        dest="source_kind",
        required=True,
        choices=("filename", "sidecar", "csv"),
        help="nhãn nằm ở đâu trong dataset gốc",
    )
    parser.add_argument("--src", type=Path, required=True, help="thư mục dataset đã giải nén")
    parser.add_argument("--golden-dir", type=Path, default=DEFAULT_GOLDEN_DIR)
    parser.add_argument("--csv", type=Path, default=None, help="đường dẫn file CSV (--from csv)")
    parser.add_argument("--image-column", default="image")
    parser.add_argument("--plate-column", default="plate")
    parser.add_argument(
        "--pattern", default=DEFAULT_FILENAME_PATTERN, help="regex có nhóm `plate` (--from filename)"
    )
    parser.add_argument(
        "--tags", default="", help="tag gắn cho MỌI ảnh lần nạp này, ngăn bởi dấu phẩy"
    )
    parser.add_argument("--source-name", default="", help="ghi nguồn dataset vào manifest")
    parser.add_argument("--limit", type=int, default=0, help="chỉ nạp N ảnh đầu (0 = tất cả)")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="xoá sạch manifest cũ thay vì nối thêm (KHÔNG xoá file ảnh đã có)",
    )
    parser.add_argument("--dry-run", action="store_true", help="chỉ in ra, không ghi gì")
    args = parser.parse_args()

    src: Path = args.src.expanduser().resolve()
    if not src.is_dir():
        raise SystemExit(f"Không thấy thư mục dataset: {src}")

    print(f"Quét {src} (kiểu: {args.source_kind}) ...")
    if args.source_kind == "filename":
        pairs = collect_from_filename(src, args.pattern)
    elif args.source_kind == "sidecar":
        pairs = collect_from_sidecar(src)
    else:
        csv_path = (args.csv or (src / "labels.csv")).expanduser().resolve()
        pairs = collect_from_csv(src, csv_path, args.image_column, args.plate_column)

    if args.limit:
        pairs = pairs[: args.limit]
    if not pairs:
        print("Không nạp được ảnh nào — kiểm lại --from / --pattern / --csv.")
        return 1

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    golden_dir: Path = args.golden_dir
    images_dir = golden_dir / "images"
    manifest_path = golden_dir / "manifest.json"

    manifest: Dict[str, object] = {"version": 1, "images_dir": "images", "items": []}
    if manifest_path.exists() and not args.replace:
        with manifest_path.open(encoding="utf-8") as fh:
            manifest = json.load(fh)

    items: List[Dict[str, object]] = list(manifest.get("items") or [])
    # Hash là khoá chống trùng: cùng một ảnh nạp hai lần từ hai dataset vẫn chỉ
    # vào bộ vàng một lần, nếu không mẫu nào trùng sẽ được tính điểm hai lượt.
    seen_hashes = {str(item.get("sha256")) for item in items if item.get("sha256")}

    added = 0
    duplicates = 0
    for image, plate in pairs:
        digest = sha256_of(image)
        if digest in seen_hashes:
            duplicates += 1
            continue
        seen_hashes.add(digest)

        target_name = f"{digest[:12]}{image.suffix.lower()}"
        entry: Dict[str, object] = {
            "file": target_name,
            "plate": plate.strip().upper(),
            "sha256": digest,
            "source": args.source_name or src.name,
        }
        if tags:
            entry["tags"] = tags

        if not args.dry_run:
            images_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image, images_dir / target_name)
        items.append(entry)
        added += 1

    manifest["items"] = items
    manifest["version"] = int(manifest.get("version") or 1)
    manifest["images_dir"] = "images"
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    if not manifest.get("created_at"):
        manifest["created_at"] = manifest["updated_at"]

    print(f"\n  thêm mới : {added}")
    print(f"  trùng hash: {duplicates}")
    print(f"  tổng bộ vàng: {len(items)}")

    if args.dry_run:
        print("\n(dry-run — chưa ghi gì)")
        return 0

    golden_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nĐã ghi {display_path(manifest_path)}")
    print("Kiểm lại nhãn bằng mắt rồi chạy: python training/eval_plates.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
