"""Điểm import tập trung cho stub sinh từ `proto/*.proto`.

Nạp ĐỘNG: quét mọi cặp `<name>_pb2` / `<name>_pb2_grpc` trong `generated/` rồi
phơi ra qua `get_stub()`. Nhờ vậy thêm 1 file proto mới KHÔNG phải sửa file này
— chỉ cần chạy lại `compile_proto.py`.
"""
import importlib
import pkgutil
from types import ModuleType
from typing import Dict, Tuple

GENERATED_PACKAGE = "app.api.grpc.generated"

PROTO_NOT_COMPILED = (
    "Chưa có stub gRPC. Chạy `python app/script/compile_proto.py` trước khi khởi động server."
)

# {"vision_service": (vision_service_pb2, vision_service_pb2_grpc), ...}
_STUBS: Dict[str, Tuple[ModuleType, ModuleType]] = {}


def _discover() -> None:
    try:
        package = importlib.import_module(GENERATED_PACKAGE)
    except ImportError:
        return

    names = {m.name for m in pkgutil.iter_modules(package.__path__)}
    for name in sorted(names):
        if not name.endswith("_pb2"):
            continue
        grpc_name = f"{name}_grpc"
        if grpc_name not in names:
            continue  # proto không khai service nào
        try:
            _STUBS[name[: -len("_pb2")]] = (
                importlib.import_module(f"{GENERATED_PACKAGE}.{name}"),
                importlib.import_module(f"{GENERATED_PACKAGE}.{grpc_name}"),
            )
        except ImportError:
            continue


_discover()

STUBS_READY = bool(_STUBS)


def get_stub(proto_name: str) -> Tuple[ModuleType, ModuleType]:
    """Trả `(pb2, pb2_grpc)` của một file proto, ví dụ `get_stub("vision_service")`."""
    if proto_name not in _STUBS:
        raise RuntimeError(
            f"Thiếu stub cho '{proto_name}.proto'. {PROTO_NOT_COMPILED}"
        )
    return _STUBS[proto_name]


def available_stubs() -> Tuple[str, ...]:
    return tuple(_STUBS)


def require_stubs(*proto_names: str) -> None:
    """Chặn sớm ở entrypoint thay vì để handler nổ giữa chừng."""
    if not STUBS_READY:
        raise RuntimeError(PROTO_NOT_COMPILED)
    missing = [name for name in proto_names if name not in _STUBS]
    if missing:
        raise RuntimeError(f"Thiếu stub cho: {', '.join(missing)}. {PROTO_NOT_COMPILED}")
