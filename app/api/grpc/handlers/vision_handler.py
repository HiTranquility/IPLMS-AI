"""Handler gRPC cho VisionService (ANPR, phân loại xe, chống tráo xe)."""
import asyncio
import time

from app.api.grpc.generated_stubs import get_stub
from app.api.grpc.mappers.vision_mapper import (
    to_recognize_plate_command,
    to_recognize_plate_response,
    to_vehicle_match_query,
    to_verify_vehicle_match_response,
)
from app.core.vision.services.anpr_service import AnprService
from app.core.vision.services.anti_fraud_service import anti_fraud_service
from app.util.logger import logger

_, _pb2_grpc = get_stub("vision_service")


class VisionHandler(_pb2_grpc.VisionServiceServicer):
    async def RecognizePlate(self, request, context):
        started = time.perf_counter()
        command = to_recognize_plate_command(request)
        logger.info(
            f"VisionService.RecognizePlate lane={command.lane_id} bytes={len(command.image_data)}"
        )

        # YOLO + OCR là CPU-bound: đẩy sang thread pool để không chẹn event loop.
        result = await asyncio.to_thread(AnprService.recognize_bytes, command)
        return to_recognize_plate_response(result, (time.perf_counter() - started) * 1000)

    async def VerifyVehicleMatch(self, request, context):
        query = to_vehicle_match_query(request)
        logger.info(
            f"VisionService.VerifyVehicleMatch expected={query.expected_vehicle_type} "
            f"current={query.current_vehicle_type}"
        )
        return to_verify_vehicle_match_response(anti_fraud_service.verify_vehicle_match(query))
