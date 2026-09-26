"""Handler gRPC cho DatasetService (ISSUE-010 — vòng dữ liệu ANPR).

Chỉ chứa LUẬT: chất lượng ảnh, chọn mẫu cho người review, khoá snapshot.
Hàng đợi, nhãn, ảnh và quyền nằm ở backend.
"""
import asyncio

from app.api.grpc.generated_stubs import get_stub
from app.api.grpc.mappers.dataset_mapper import (
    to_evaluate_response,
    to_snapshot_response,
    to_snapshot_samples,
)
from app.core.dataset.services import CurationService, SnapshotService
from app.util.logger import logger

_, _pb2_grpc = get_stub("dataset_service")


class DatasetHandler(_pb2_grpc.DatasetServiceServicer):
    async def EvaluateCapture(self, request, context):
        # Giải mã + đo ảnh là CPU-bound (OpenCV) → thread pool.
        result = await asyncio.to_thread(
            CurationService.evaluate_capture,
            request.image_data,
            model_confidence=request.model_confidence if request.has_model_confidence else None,
            human_corrected=request.human_corrected,
            low_confidence_threshold=request.low_confidence_threshold or 0.75,
            random_audit_rate=request.random_audit_rate,
        )
        logger.info(
            "DatasetService.EvaluateCapture selected=%s reasons=%s",
            result.selected,
            ",".join(result.reasons),
        )
        return to_evaluate_response(result)

    async def BuildSnapshot(self, request, context):
        # dataset_id rỗng / mẫu trùng / split lạ → ValueError → INVALID_ARGUMENT.
        lock = SnapshotService.build_lock(request.dataset_id, to_snapshot_samples(request))
        logger.info("DatasetService.BuildSnapshot dataset=%s samples=%d", lock["dataset_id"], lock["sample_count"])
        return to_snapshot_response(lock)
