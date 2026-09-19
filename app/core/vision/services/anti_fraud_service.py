"""Nghiệp vụ Chống Gian Lận (Anti-Fraud Gatekeeper).

So khớp loại xe giữa Check-in và Check-out để ngăn tráo xe.

[GOTCHA] ``similarity_score`` LUÔN là ``0.0`` — nghĩa là "chưa đo", không phải
"giống nhau 0%". Phép so ẢNH CROP (ReID/siamese trên ảnh xe) chưa được triển
khai, nên không có điểm tương đồng nào để trả.

Bản trước trả hằng số ``0.35``/``0.98`` cho hai nhánh, khiến mọi response trông
như đã qua một phép đo thị giác. Không có phép đo nào cả. Backend hiện chỉ quyết
định bằng ``is_matched`` + ``mismatch_reason`` (xem
``staff-operation.service.ts:286-289``), nên bỏ con số bịa KHÔNG đổi hành vi
nghiệp vụ — nó chỉ thôi nói dối trong log và trên màn hình nhân viên.
"""
from app.core.constants import SIMILARITY_NOT_MEASURED
from app.core.enums import FraudReason
from app.core.vision.dtos.vision_dto import VehicleMatchQuery, VehicleMatchResult
from app.utils.logger import logger


class AntiFraudService:
    @staticmethod
    def verify_vehicle_match(query: VehicleMatchQuery) -> VehicleMatchResult:
        logger.info(
            f"Verifying vehicle match: expected={query.expected_vehicle_type}, "
            f"current={query.current_vehicle_type}"
        )

        if query.expected_vehicle_type and query.current_vehicle_type:
            if query.expected_vehicle_type.lower() != query.current_vehicle_type.lower():
                logger.warning(
                    f"🚨 FRAUD DETECTED: Vehicle type mismatch! "
                    f"In={query.expected_vehicle_type}, Out={query.current_vehicle_type}"
                )
                return VehicleMatchResult(
                    is_matched=False,
                    similarity_score=SIMILARITY_NOT_MEASURED,
                    mismatch_reason=FraudReason.VEHICLE_TYPE_MISMATCH,
                )

        # [MUST] Còn thiếu: so khớp ảnh crop (checkin_crop_url vs checkout_crop_url)
        # bằng embedding ReID — SUGGESTION-007 B6. Tới lúc đó `similarity_score` mới có
        # số thật, và `PLATE_TAMPERING_SUSPECTED` mới có nghĩa (hiện khai rồi
        # nhưng không nhánh nào raise).
        #
        # [NEVER] gán một hằng số vào đây cho "đủ hình dạng response".
        return VehicleMatchResult(
            is_matched=True,
            similarity_score=SIMILARITY_NOT_MEASURED,
            mismatch_reason=FraudReason.OK,
        )


anti_fraud_service = AntiFraudService()
