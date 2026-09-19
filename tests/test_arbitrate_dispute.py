"""`ArbitrateDispute` phải TỪ CHỐI, không được trả phán quyết bịa.

Bản cũ luôn trả `APPROVE_REFUND` hoàn đúng số tiền khách đòi, kèm lý do bịa về
"barie quét vé chậm 15 phút" và một URL bằng chứng không tồn tại — bất kể khiếu
nại là gì. Nó không tự chi tiền, nhưng nhân viên đọc được một kết luận thẩm định
trông chính thức như vậy thì rất khó cãi.

Test này khoá lại trạng thái "từ chối thẳng thắn". Ai bật lại mà chưa có phần
thẩm định thật phía sau sẽ làm đỏ ở đây trước khi kịp deploy.
"""
import asyncio
import unittest

import grpc

from app.api.grpc.interceptors.logging_interceptor import status_for
from app.core.copilot.dtos.copilot_dto import DisputeArbitrationRequest
from app.core.copilot.services.copilot_service import copilot_service
from app.core.exceptions import AiServiceError, FeatureNotImplementedError

KHIEU_NAI = DisputeArbitrationRequest(
    dispute_id="DSP-123456",
    session_id="sess-abc",
    claim_reason="Hệ thống tính sai tiền",
    claimed_amount=10_000_000.0,
)


class ArbitrateDisputeTuChoiTest(unittest.TestCase):
    def test_nem_loi_thay_vi_tra_phan_quyet(self):
        with self.assertRaises(FeatureNotImplementedError):
            asyncio.run(copilot_service.arbitrate_dispute(KHIEU_NAI))

    def test_khong_he_nhac_toi_so_tien_khach_doi(self):
        """Số tiền trong thông báo lỗi = đã lỡ xác nhận con số khách tự khai."""
        try:
            asyncio.run(copilot_service.arbitrate_dispute(KHIEU_NAI))
        except FeatureNotImplementedError as exc:
            self.assertNotIn("10.000.000", str(exc))
            self.assertNotIn("10000000", str(exc))
        else:
            self.fail("Phải ném FeatureNotImplementedError")

    def test_khong_bia_bang_chung(self):
        try:
            asyncio.run(copilot_service.arbitrate_dispute(KHIEU_NAI))
        except FeatureNotImplementedError as exc:
            loi = str(exc).lower()
            self.assertNotIn("barie", loi)
            self.assertNotIn("storage.iplms.vn", loi)
        else:
            self.fail("Phải ném FeatureNotImplementedError")

    def test_van_la_loi_nghiep_vu_de_interceptor_bat_duoc(self):
        self.assertTrue(issubclass(FeatureNotImplementedError, AiServiceError))


class QuyVeGrpcStatusTest(unittest.TestCase):
    def test_map_sang_unimplemented_chu_khong_phai_internal(self):
        """UNIMPLEMENTED nói đúng sự thật và client KHÔNG retry. INTERNAL sẽ khiến
        NestJS coi đây là sự cố hạ tầng rồi thử lại một việc vốn không tồn tại."""
        self.assertEqual(
            grpc.StatusCode.UNIMPLEMENTED,
            status_for(FeatureNotImplementedError("chưa có")),
        )

    def test_khong_nuot_mat_cac_loi_khac(self):
        """Dòng mới chèn vào bảng ánh xạ không được che lớp cha AiServiceError."""
        self.assertEqual(grpc.StatusCode.INTERNAL, status_for(AiServiceError("loi khac")))


if __name__ == "__main__":
    unittest.main()
