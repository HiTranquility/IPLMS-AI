"""Handler gRPC cho DatasetService (ISSUE-010 — vòng dữ liệu ANPR).

Chỉ chứa LUẬT: chất lượng ảnh, chọn mẫu cho người review, khoá snapshot.
Hàng đợi, nhãn, ảnh và quyền nằm ở backend.
"""
import asyncio

from app.api.grpc.generated_stubs import get_stub
from app.api.grpc.mappers.dataset_mapper import (
    to_accept_policy_response,
    to_evaluate_response,
    to_export_response,
    to_exported_captures,
    to_evaluation_samples,
    to_progress_event,
    to_result_event,
    to_snapshot_response,
    to_snapshot_samples,
)
from app.core.dataset.services import CurationService, SnapshotService, evaluation_service
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

    async def EvaluateSnapshot(self, request, context):
        # Mỗi ảnh chạy ANPR (CPU-bound) trong thread pool; lỗi từng ảnh thành một
        # dòng số liệu chứ không huỷ cả lượt. Client ngắt stream → vòng lặp dừng.
        samples = to_evaluation_samples(request)
        if not samples:
            raise ValueError("Snapshot không có mẫu test-golden nào để đo")
        rows = []
        for idx, sample in enumerate(samples, start=1):
            rows.append(await asyncio.to_thread(evaluation_service.evaluate_one, sample))
            yield to_progress_event(idx, len(samples))
        summary = await asyncio.to_thread(evaluation_service.summarize, rows)
        version = await asyncio.to_thread(evaluation_service.model_version)
        logger.info(
            "DatasetService.EvaluateSnapshot eval=%s samples=%d strict=%.3f",
            request.evaluation_id,
            len(rows),
            summary.get("exact_match_strict", 0.0),
        )
        yield to_result_event(version, summary)

    async def ExportForConsole(self, request, context):
        # IPLMS ADR-0048 §5 (A2): ghi vào DB `ai_console`. Nhập trễ nạp để process
        # inference không cần cấu hình console khi backend chưa bật kênh xuất.
        from app.core.console.services.vision_import_service import console_vision_import_service

        result = await console_vision_import_service.import_batch(to_exported_captures(request))
        logger.info(
            "DatasetService.ExportForConsole accepted=%d rejected=%d",
            result["accepted"],
            result["rejected"],
        )
        return to_export_response(result)

    async def GetAcceptPolicy(self, request, context):
        # IPLMS ADR-0051: backend kéo ngưỡng đã duyệt; chỉ đọc DB `ai_console`.
        from app.core.console.services.accept_policy_service import console_accept_policy_service

        policy = await console_accept_policy_service.approved(request.model_name)
        logger.info(
            "DatasetService.GetAcceptPolicy model=%s found=%s version=%s",
            request.model_name or "anpr",
            policy is not None,
            policy["version"] if policy else "-",
        )
        return to_accept_policy_response(policy)
