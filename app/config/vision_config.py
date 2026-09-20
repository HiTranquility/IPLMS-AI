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
    device: str = "cpu"

    # CNN phân loại loại xe (stage tùy chọn — tắt khi không có checkpoint).
    vehicle_model: str = "NetV2"
    vehicle_checkpoint: str = ""
    vehicle_model_version: str = "v1"
    vehicle_artifact_url: str = ""
    vehicle_artifact_sha256: str = ""
    vehicle_num_classes: int = 4
    vehicle_img_size: int = 32
    vehicle_labels: str = "car_sedan,car_suv,motorbike,truck"

    @property
    def ocr_language_list(self) -> List[str]:
        return [lang.strip() for lang in self.ocr_languages.split(",") if lang.strip()]

    @property
    def vehicle_label_list(self) -> List[str]:
        return [label.strip() for label in self.vehicle_labels.split(",") if label.strip()]
