"""Cấu hình Domain Vision: YOLO phát hiện biển, EasyOCR, CNN phân loại xe."""
from typing import List

from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class VisionConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_")

    # Cổng mặc định gán cho ảnh không kèm lane_id.
    lane_id: str = "gate_in_01"

    # Model local giữ tương thích; URL + SHA-256 dùng khi lấy từ object storage.
    yolo_model_path: str = "model/artifacts/bootstrap/anpr/best.pt"
    yolo_model_version: str = "bootstrap-v1"
    yolo_artifact_url: str = ""
    yolo_artifact_sha256: str = ""
    ocr_languages: str = "en,vi"
    # Thư mục lưu model EasyOCR. Rỗng = để EasyOCR dùng EASYOCR_MODULE_PATH env
    # hoặc ~/.EasyOCR/ mặc định. setup-dev script đặt vào var/easyocr-cache/.
    ocr_model_storage_dir: str = ""
    # True (production): nạp model XONG mới mở cổng/readiness.
    # False (dev): mở cổng ngay, nạp model ở nền vào cache volume.
    vision_warmup_on_start: bool = True
    device: str = "auto"

    @property
    def resolved_device(self) -> str:
        dev = (self.device or "auto").lower()
        if dev in ("auto", "cuda"):
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
            except Exception:
                pass
            return "cpu"
        return dev

    # Tăng tốc ANPR bằng ONNX Runtime (AI_ONNX_ENABLED và AI_ONNX_MODEL_DIR)
    onnx_enabled: bool = True
    onnx_model_dir: str = "data/models"

    # CNN phân loại loại xe (stage tùy chọn — tắt khi không có checkpoint).
    vehicle_model: str = "NetV2"
    vehicle_checkpoint: str = ""
    vehicle_model_version: str = "v1"
    vehicle_artifact_url: str = ""
    vehicle_artifact_sha256: str = ""
    vehicle_num_classes: int = 4
    vehicle_img_size: int = 32
    vehicle_labels: str = "car_sedan,car_suv,motorbike,truck"
    # Xác suất softmax cao nhất dưới ngưỡng → trả "không rõ" (None) thay vì đoán.
    vehicle_min_confidence: float = 0.6

    # Đọc biển số từ clip ở AI Console (IPLMS REQ-021 A). Clip không được lưu.
    clip_max_bytes: int = 50 * 1024 * 1024
    clip_max_duration_s: float = 60.0
    # Trần số frame đưa vào ANPR mỗi clip — chặn thời gian CPU dù nhịp cắt nhỏ.
    clip_max_frames: int = 240
    clip_sample_interval_s: float = 0.5
    # Chế độ "theo chuyển động": bỏ frame có tỉ lệ điểm ảnh đổi (so frame giữ trước) dưới ngưỡng.
    clip_motion_threshold: float = 0.01
    # Gộp frame thành sự kiện: ô biển chồng nhau đủ IoU, hai lần thấy cách nhau không quá max_gap.
    clip_event_iou: float = 0.3
    clip_event_max_gap_s: float = 1.5

    @property
    def ocr_language_list(self) -> List[str]:
        return [lang.strip() for lang in self.ocr_languages.split(",") if lang.strip()]

    @property
    def vehicle_label_list(self) -> List[str]:
        return [label.strip() for label in self.vehicle_labels.split(",") if label.strip()]
