"""Optional vehicle-type stage: the teacher's CNN (NetV1/NetV2) as a classifier."""
import io
import threading
from pathlib import Path
from typing import Optional

from app.config import get_config
from app.infra.model_registry import (
    ArtifactResolutionError,
    ModelArtifactSpec,
    get_model_artifact_registry,
)
from app.util.logger import logger

_state: dict = {"init": False, "model": None, "device": None, "labels": None, "tf": None}
_load_lock = threading.Lock()


def _load_checkpoint_safely(torch_mod, checkpoint_path: Path, device, has_verified_sha256: bool):
    try:
        return torch_mod.load(checkpoint_path, map_location=device, weights_only=True)
    except TypeError:
        # Phiên bản torch cũ chưa có tham số weights_only
        return torch_mod.load(checkpoint_path, map_location=device)
    except Exception as exc:
        if not has_verified_sha256:
            raise ValueError(
                "Checkpoint yêu cầu unpickle tuỳ chỉnh nhưng thiếu AI_VEHICLE_ARTIFACT_SHA256 đã xác thực"
            ) from exc
        logger.warning(
            "Checkpoint phân loại xe không nạp được với weights_only=True (%s); "
            "fallback weights_only=False vì đã xác thực SHA-256.",
            str(exc)[:200],
        )
        return torch_mod.load(checkpoint_path, map_location=device, weights_only=False)


def _ensure_loaded() -> bool:
    if _state["init"]:
        return _state["model"] is not None

    with _load_lock:
        if _state["init"]:
            return _state["model"] is not None

        vision = get_config().vision
        if not vision.vehicle_checkpoint and not vision.vehicle_artifact_url:
            _state["init"] = True
            return False

        try:
            if len(vision.vehicle_label_list) != vision.vehicle_num_classes:
                raise ValueError("AI_VEHICLE_LABELS must match AI_VEHICLE_NUM_CLASSES")

            import torch
            import torchvision.transforms as T
            from model.architectures.m1.nets import NetV1
            from model.architectures.m2.nets import NetV2

            checkpoint_name = Path(vision.vehicle_checkpoint).name or "vehicle-classifier.pth"
            checkpoint_path = get_model_artifact_registry().resolve(
                ModelArtifactSpec(
                    name="vehicle-classifier",
                    version=vision.vehicle_model_version,
                    file_name=checkpoint_name,
                    local_path=vision.vehicle_checkpoint,
                    source_url=vision.vehicle_artifact_url,
                    sha256=vision.vehicle_artifact_sha256,
                )
            )
            model_cls = {"NetV1": NetV1, "NetV2": NetV2}.get(vision.vehicle_model, NetV2)
            device = torch.device(
                "cuda" if vision.device.lower() == "cuda" and torch.cuda.is_available() else "cpu"
            )
            model = model_cls(n_class=vision.vehicle_num_classes).to(device)

            ckpt = _load_checkpoint_safely(
                torch,
                Path(checkpoint_path),
                device,
                has_verified_sha256=bool((vision.vehicle_artifact_sha256 or "").strip()),
            )
            state = (
                ckpt.get("model_state_dict") or ckpt.get("state_dict") or ckpt
                if isinstance(ckpt, dict)
                else ckpt
            )
            state = {(k[7:] if k.startswith("module.") else k): v for k, v in state.items()}
            # strict: checkpoint lệch kiến trúc/số lớp mà nạp "lỏng" thì các lớp
            # thiếu giữ trọng số khởi tạo ngẫu nhiên — model vẫn trả nhãn, chỉ là
            # nhãn rác, và chống gian lận đem nhãn rác đó đi so.
            model.load_state_dict(state, strict=True)
            model.eval()
        except (ArtifactResolutionError, ValueError, OSError, RuntimeError) as exc:
            logger.error(
                "Không thể nạp tầng phân loại xe tuỳ chọn (%s); tắt tầng phân loại để không chặn ANPR: %s",
                vision.vehicle_model,
                str(exc)[:300],
            )
            _state.update(init=True, model=None)
            return False

        _state.update(
            init=True,
            model=model,
            device=device,
            labels=vision.vehicle_label_list,
            min_confidence=vision.vehicle_min_confidence,
            tf=T.Compose(
                [T.Resize((vision.vehicle_img_size, vision.vehicle_img_size)), T.ToTensor()]
            ),
        )
        return True


def classify_vehicle(
    image_bytes: bytes,
    plate_number: Optional[str] = None,
    plate_color: Optional[str] = None,
) -> Optional[str]:
    """Return a measured CNN label; plate metadata must never override visual evidence.

    Optional metadata arguments are accepted for compatibility with callers from
    the integration branch. A missing model or weak prediction remains unknown.
    """
    if not _ensure_loaded():
        return None
    import torch
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    x = _state["tf"](img).unsqueeze(0).to(_state["device"])
    with torch.no_grad():
        probabilities = torch.softmax(_state["model"](x), dim=1)[0]
    confidence, idx = (float(value) for value in probabilities.max(dim=0))
    if confidence < _state["min_confidence"]:
        return None
    labels = _state["labels"]
    return labels[int(idx)] if int(idx) < len(labels) else str(int(idx))
