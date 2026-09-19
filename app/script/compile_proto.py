"""Sinh stub Python từ các file `proto/*.proto` vào `app/api/grpc/generated/`.

Chạy: `python app/script/compile_proto.py` (từ thư mục `ai/`).
Hỗ trợ cả file proto gộp hoặc các file proto tách rời theo từng nghiệp vụ
(vision_service.proto, copilot_service.proto, forecast_service.proto).
"""
import subprocess
import sys
from pathlib import Path

# Set utf-8 stdout
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

AI_ROOT = Path(__file__).resolve().parents[2]  # .../ai
REPO_ROOT = AI_ROOT.parent
OUT_DIR = AI_ROOT / "app" / "api" / "grpc" / "generated"
GENERATED_PACKAGE = "app.api.grpc.generated"


def find_proto_files() -> list[Path]:
    """Tìm tất cả file .proto trong proto/ gốc repo hoặc ai/proto/."""
    for proto_dir in (REPO_ROOT / "proto", AI_ROOT / "proto"):
        if proto_dir.exists():
            protos = list(proto_dir.glob("*.proto"))
            if protos:
                return protos
    print(f"❌ Không tìm thấy file .proto tại {REPO_ROOT / 'proto'} hoặc {AI_ROOT / 'proto'}")
    sys.exit(1)


def rewrite_stub_imports() -> None:
    """protoc sinh `import <name>_pb2` phẳng — sửa thành import tuyệt đối theo package."""
    for stub in OUT_DIR.glob("*_pb2_grpc.py"):
        content = stub.read_text(encoding="utf-8")
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("import ") and "_pb2 as " in line:
                # import vision_service_pb2 as vision__service__pb2 -> from app.api.grpc.generated import vision_service_pb2 as ...
                module_name = line.split()[1]
                new_line = line.replace(f"import {module_name}", f"from {GENERATED_PACKAGE} import {module_name}")
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        stub.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def compile_proto() -> None:
    protos = find_proto_files()
    proto_dir = protos[0].parent
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    init_file = OUT_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Stub gRPC sinh tự động — đừng sửa tay."""\n', encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{proto_dir}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
    ] + [str(p) for p in protos]

    print(f"🔨 Đang biên dịch {len(protos)} file proto từ {proto_dir} -> {OUT_DIR}:")
    for p in protos:
        print(f"   ├─ {p.name}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Lỗi biên dịch Protobuf:")
        print(result.stderr)
        sys.exit(result.returncode)

    rewrite_stub_imports()
    print(f"✅ Biên dịch thành công! Tất cả Stubs đã nằm tại {OUT_DIR}")


if __name__ == "__main__":
    compile_proto()
