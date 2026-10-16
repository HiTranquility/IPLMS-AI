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
    async def recognize(file, lane_id: Optional[str] = None) -> PlateResult:
        """Đường REST: nhận UploadFile rồi uỷ cho `recognize_bytes`."""
        image_bytes = await file.read()
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
        from app.core.vision.engines.anpr_engine import run_anpr

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
