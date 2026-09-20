"""Optional vehicle-type stage: the teacher's CNN (NetV1/NetV2) as a classifier."""
import io
import threading
from pathlib import Path
from typing import Optional

from app.config import get_config
from app.infra.model_registry import ModelArtifactSpec, get_model_artifact_registry

_state: dict = {"init": False, "model": None, "device": None, "labels": None, "tf": None}
_load_lock = threading.Lock()

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
        device = torch.device("cuda" if vision.device.lower() == "cuda" and torch.cuda.is_available() else "cpu")
        model = model_cls(n_class=vision.vehicle_num_classes).to(device)

        try:
            ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
        except TypeError:
            ckpt = torch.load(checkpoint_path, map_location=device)
        state = ckpt.get("model_state_dict") or ckpt.get("state_dict") or ckpt if isinstance(ckpt, dict) else ckpt
        state = {(k[7:] if k.startswith("module.") else k): v for k, v in state.items()}
        model.load_state_dict(state, strict=False)
        model.eval()

        _state.update(
            init=True,
            model=model,
            device=device,
            labels=vision.vehicle_label_list,
            tf=T.Compose([T.Resize((vision.vehicle_img_size, vision.vehicle_img_size)), T.ToTensor()]),
        )
        return True

def classify_vehicle(image_bytes: bytes) -> Optional[str]:
    if not _ensure_loaded():
        return None
    import torch
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    x = _state["tf"](img).unsqueeze(0).to(_state["device"])
    with torch.no_grad():
        idx = int(_state["model"](x).argmax(dim=1).item())
    labels = _state["labels"]
    return labels[idx] if idx < len(labels) else str(idx)
