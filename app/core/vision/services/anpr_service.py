"""Điều phối 1 lượt ANPR: phát hiện biển → OCR → phân loại xe."""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.config import get_config
from app.core.vision.dtos.vision_dto import PlateResult, RecognizePlateCommand
from app.core.vision.engines.vehicle_classifier import classify_vehicle
from app.util.file import save_bytes_image
from app.util.generate_url import generate_cropped_image_url, generate_original_image_url


class AnprService:
    @staticmethod
    async def recognize(image_bytes: bytes, lane_id: Optional[str] = None) -> PlateResult:
        """Đường REST: nhận bytes đã qua `read_image_upload` (giới hạn byte, định dạng) rồi uỷ cho `recognize_bytes`."""
        command = RecognizePlateCommand(image_data=image_bytes, lane_id=lane_id)
        # YOLO + OCR là CPU-bound — đừng chẹn event loop của FastAPI.
        return await asyncio.to_thread(AnprService.recognize_bytes, command, True)

    @staticmethod
    def recognize_bytes(
        command: RecognizePlateCommand,
        persist_files: bool = False,
    ) -> PlateResult:
        """Nhận diện từ raw bytes — dùng chung cho cả gRPC lẫn REST.

        `persist_files` CHỈ bật ở đường REST: hợp đồng REST trả URL nên phải có
        file thật trên đĩa. Đường gRPC thì không — backend nhận `crop_bytes` rồi
        tự đẩy lên StorageProvider, nên ghi thêm một bản xuống `static/` chỉ tổ
        tốn I/O trên đường nóng và làm đầy dần ổ đĩa tạm của pod (không có cơ
        chế dọn nào cả).
        """
        from app.core.vision.engines.anpr.engine import run_anpr

        result = run_anpr(command.image_data)
        plate_number = result["plate_number"]
        # Sinh trước vì tên file ảnh khoá theo event_id (xem generate_url).
        event_id = f"evt_{uuid.uuid4().hex[:12]}"

        crop_url = ""
        original_url = None
        if persist_files:
            crop_url = generate_cropped_image_url(plate_number, event_id)
            save_bytes_image(result["crop_bytes"], crop_url)
            original_url = generate_original_image_url(plate_number, event_id)
            save_bytes_image(command.image_data, original_url)

        plate_color = result.get("plate_color")

        # Phân loại ảnh bằng CNN; không suy diễn loại xe từ biển số/màu nền.
        vehicle_type = (
            classify_vehicle(
                command.image_data,
                plate_number=plate_number,
                plate_color=plate_color,
            )
            if command.classify_vehicle
            else None
        )

        return PlateResult(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            lane_id=command.lane_id or get_config().vision.lane_id,
            plate_number=plate_number,
            crop_image_url=crop_url,
            original_image_url=original_url,
            vehicle_type=vehicle_type,
            confidence=result["confidence"],
            process_time=result["process_time"],
            crop_bytes=result["crop_bytes"],
            plate_color=plate_color,
        )

    @staticmethod
    def recognize_clip(data: bytes, content_type: str, motion: bool = False) -> dict:
        """Đọc biển số từ một clip (IPLMS REQ-021 A), trả sự kiện đã gộp theo xe.

        Không ghi gì xuống đĩa ngoài file tạm của OpenCV (xoá ngay trong engine):
        clip là PII, lượt chạy chỉ trả ảnh cắt biển của frame tốt nhất.

        Raises:
            ValueError: sai định dạng, vượt dung lượng/độ dài cấu hình.
        """
        from app.core.vision.engines.anpr.engine import run_anpr
        from app.core.vision.engines.anpr.video import CLIP_SUFFIXES, ClipLimits, analyze_clip

        cfg = get_config().vision
        suffix = CLIP_SUFFIXES.get((content_type or "").split(";")[0].strip().lower())
        if suffix is None:
            raise ValueError("Chỉ nhận clip MP4 hoặc WebM.")
        if not data:
            raise ValueError("Clip rỗng.")
        if len(data) > cfg.clip_max_bytes:
            raise ValueError(f"Clip vượt {cfg.clip_max_bytes // (1024 * 1024)} MB.")
        limits = ClipLimits(
            max_duration_s=cfg.clip_max_duration_s,
            max_frames=cfg.clip_max_frames,
            sample_interval_s=cfg.clip_sample_interval_s,
            motion_threshold=cfg.clip_motion_threshold if motion else None,
        )
        return analyze_clip(data, suffix, limits, run_anpr, cfg.clip_event_iou, cfg.clip_event_max_gap_s)


anpr_service = AnprService()
