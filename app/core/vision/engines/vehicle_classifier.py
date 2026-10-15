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
        device = torch.device("cuda" if vision.device.lower() in ("cuda", "gpu", "auto") and torch.cuda.is_available() else "cpu")
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

def classify_vehicle(
    image_bytes: bytes,
    plate_number: Optional[str] = None,
    plate_color: Optional[str] = None,
) -> Optional[str]:
    """Phân loại loại phương tiện kết hợp mô hình CNN (NetV2) và quy chuẩn biển số Việt Nam."""
    import re
    from app.util.logger import logger

    # 1. Trích xuất đặc trưng từ quy chuẩn biển số Việt Nam (Vietnamese Plate Prior)
    plate_prior = None
    if plate_number and plate_number != "UNKNOWN":
        p = plate_number.upper().strip()
        clean = re.sub(r'[^A-Z0-9]', '', p)

        # 1. Nhận diện xe máy (mô tô 2 bánh): sê-ri 2 ký tự (vd: 59-V1-, 59V1- hoặc không dấu 9 ký tự: 59V179379)
        is_moto = False
        if re.match(r'^\d{2}-[A-Z][0-9A-Z]-', p):
            is_moto = True
        elif re.match(r'^\d{2}[A-Z][0-9A-Z]-', p):
            is_moto = True
        elif len(clean) == 9 and re.match(r'^\d{2}[A-Z][0-9A-Z]\d{5}$', clean):
            is_moto = True

        if is_moto:
            plate_prior = "motorbike"
        else:
            # 2. Nhận diện ô tô (xe tải / xe con / xe khách)
            truck_series = False
            if re.match(r'^\d{2}[CH]-?', p) or re.match(r'^\d{2}-[CH]-?', p):
                truck_series = True
            elif len(clean) in (7, 8) and re.match(r'^\d{2}[CH]\d{4,5}$', clean):
                truck_series = True
            # Biển vàng sê-ri C, H (tải), D (xe van / bán tải chở hàng), B (xe khách / bus)
            elif plate_color == "yellow" and (re.match(r'^\d{2}[CHDB]', clean) or re.match(r'^\d{2}-[CHDB]', p)):
                truck_series = True

            if truck_series:
                plate_prior = "truck"
            elif re.match(r'^\d{2}[A-Z]-?', p) or re.match(r'^\d{2}-[A-Z]-?', p):
                plate_prior = "car_sedan"
            elif len(clean) in (7, 8) and re.match(r'^\d{2}[A-Z]\d{4,5}$', clean):
                plate_prior = "car_sedan"

    # 2. Suy luận bằng CNN (NetV2)
    has_model = _ensure_loaded()
    if not has_model:
        return plate_prior

    import torch
    from PIL import Image

    cnn_label = None
    cnn_conf = 0.0
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        x = _state["tf"](img).unsqueeze(0).to(_state["device"])
        with torch.no_grad():
            logits = _state["model"](x)
            probs = torch.softmax(logits, dim=1)
            max_prob, idx = probs.max(dim=1)
            idx = int(idx.item())
            cnn_conf = float(max_prob.item())
        labels = _state["labels"]
        cnn_label = labels[idx] if idx < len(labels) else str(idx)
    except Exception as exc:
        logger.warning(f"CNN classification inference failed: {exc}")

    # 3. Kết hợp tiên nghiệm biển số và phân loại CNN (Prior Fusion)
    if plate_prior:
        # Nếu biển số xe máy rõ ràng (ví dụ 59V1), ưu tiên quy chuẩn pháp lý
        if plate_prior == "motorbike":
            return "motorbike"
        if plate_prior == "truck":
            return "truck"
        # Biển xe con dân sự (A, E, F, G, K, S...):
        # Tuyệt đối không cho phép mô hình CNN chưa hội tụ ghi đè thành truck.
        # Chỉ tinh chỉnh chi tiết sedan vs suv nếu CNN có độ tự tin cao (>= 0.45).
        if plate_prior == "car_sedan":
            if cnn_label in ("car_sedan", "car_suv") and cnn_conf >= 0.45:
                return cnn_label
            return "car_sedan"
        return plate_prior

    return cnn_label
