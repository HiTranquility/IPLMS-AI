"""Cấu hình Domain Vision: YOLO phát hiện biển, EasyOCR, CNN phân loại xe."""
from typing import List

from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class VisionConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_")

    # Cổng mặc định gán cho ảnh không kèm lane_id.
    lane_id: str = "gate_in_01"

    # Trọng số YOLO. Tương đối so với thư mục `ai/`.
    yolo_model_path: str = "models/best.pt"
    ocr_languages: str = "en,vi"
    device: str = "cpu"

    # CNN phân loại loại xe (stage tùy chọn — tắt khi không có checkpoint).
    vehicle_model: str = "NetV2"
    vehicle_checkpoint: str = ""
    vehicle_num_classes: int = 4
    vehicle_img_size: int = 32
    vehicle_labels: str = "car_sedan,car_suv,motorbike,truck"

    @property
    def ocr_language_list(self) -> List[str]:
        return [lang.strip() for lang in self.ocr_languages.split(",") if lang.strip()]

    @property
    def vehicle_label_list(self) -> List[str]:
        return [label.strip() for label in self.vehicle_labels.split(",") if label.strip()]
