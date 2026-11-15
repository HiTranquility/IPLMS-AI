"""Xuất model phát hiện biển số ANPR từ PyTorch (`best.pt`) sang ONNX (`data/models/best.onnx`).

Chạy từ thư mục `ai/`:
    python app/script/export_anpr_onnx.py
    python app/script/export_anpr_onnx.py --force

Đặc tính:
- Tất định (idempotent): loại bỏ trường `date` biến thiên trong metadata ONNX và gắn
  `source_sha256` của file `.pt` gốc, đảm bảo hai lần xuất cho cùng SHA-256.
- An toàn nguyên tử: xuất trên bản sao tạm rồi `os.replace` vào đích sau khi đã qua
  cổng kiểm `onnx.checker` và chạy thử 1 lượt `onnxruntime.InferenceSession`.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

AI_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = AI_ROOT / "model" / "artifacts" / "bootstrap" / "anpr" / "best.pt"
DEFAULT_OUTPUT = AI_ROOT / "data" / "models" / "best.onnx"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_onnx_source_sha256(onnx_path: Path) -> str | None:
    import onnx

    if not onnx_path.is_file():
        return None
    try:
        model = onnx.load(str(onnx_path), load_external_data=False)
        for prop in model.metadata_props:
            if prop.key == "source_sha256":
                return prop.value
    except Exception:
        return None
    return None


def normalize_onnx_metadata(onnx_path: Path, source_sha256: str) -> None:
    """Loại bỏ timestamp biến thiên (`date`) và ghi cố định `source_sha256` theo thứ tự khóa."""
    import onnx

    model = onnx.load(str(onnx_path))
    props = {p.key: p.value for p in model.metadata_props if p.key != "date"}
    props["source_sha256"] = source_sha256

    del model.metadata_props[:]
    for key in sorted(props):
        entry = model.metadata_props.add()
        entry.key = key
        entry.value = props[key]

    onnx.checker.check_model(model)
    onnx.save(model, str(onnx_path))


def verify_onnx_runtime(onnx_path: Path, imgsz: int = 640) -> tuple[int, ...]:
    """Chạy thử 1 khung hình rỗng qua ONNX Runtime để đảm bảo đồ thị suy luận hợp lệ."""
    import numpy as np
    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    dummy = np.zeros((1, 3, imgsz, imgsz), dtype=np.float32)
    outputs = sess.run(None, {input_name: dummy})
    if not outputs or len(outputs[0].shape) != 3:
        raise RuntimeError(f"Output ONNX không đúng định dạng 3 chiều YOLO: {outputs[0].shape if outputs else None}")
    return tuple(int(dim) for dim in outputs[0].shape)


def export_anpr_onnx(
    source_pt: Path = DEFAULT_SOURCE,
    output_onnx: Path = DEFAULT_OUTPUT,
    imgsz: int = 640,
    opset: int = 17,
    force: bool = False,
) -> Path:
    if not source_pt.is_file():
        raise FileNotFoundError(f"Không tìm thấy trọng số PyTorch nguồn: {source_pt}")

    src_hash = sha256_file(source_pt)
    if output_onnx.is_file() and not force:
        existing_src_hash = read_onnx_source_sha256(output_onnx)
        if existing_src_hash == src_hash:
            out_hash = sha256_file(output_onnx)
            print(f"✅ Đã có sẵn model ONNX khớp nguồn ({output_onnx}) | sha256={out_hash[:16]}...")
            return output_onnx

    from ultralytics import YOLO

    output_onnx.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="iplms-onnx-export-") as tmp_dir:
        tmp_pt = Path(tmp_dir) / "best.pt"
        shutil.copy2(source_pt, tmp_pt)

        yolo = YOLO(str(tmp_pt))
        exported_str = yolo.export(format="onnx", imgsz=imgsz, opset=opset, simplify=False)
        exported_path = Path(exported_str)

        normalize_onnx_metadata(exported_path, source_sha256=src_hash)
        out_shape = verify_onnx_runtime(exported_path, imgsz=imgsz)

        staging_target = output_onnx.with_suffix(f".{os.getpid()}.tmp.onnx")
        try:
            shutil.copy2(exported_path, staging_target)
            os.replace(staging_target, output_onnx)
        finally:
            if staging_target.exists():
                staging_target.unlink()

    out_hash = sha256_file(output_onnx)
    print(
        f"✅ Xuất thành công ANPR ONNX: {output_onnx} "
        f"(shape={out_shape}, opset={opset}, sha256={out_hash})"
    )
    return output_onnx


def main() -> int:
    parser = argparse.ArgumentParser(description="Xuất trọng số YOLO ANPR sang ONNX tất định.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Đường dẫn tới best.pt")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Đường dẫn xuất best.onnx")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh đầu vào vuông (mặc định: 640)")
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset version (mặc định: 17)")
    parser.add_argument("--force", action="store_true", help="Xuất đè kể cả khi SHA-256 nguồn không đổi")
    args = parser.parse_args()

    export_anpr_onnx(
        source_pt=args.source.resolve(),
        output_onnx=args.output.resolve(),
        imgsz=args.imgsz,
        opset=args.opset,
        force=args.force,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
