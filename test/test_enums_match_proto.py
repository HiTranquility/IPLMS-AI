"""Enum Python phải khớp TỪNG CHỮ với enum trong proto.

`core/enums.py` ghi rõ ràng buộc này, nhưng ràng buộc chỉ nằm trong comment thì
sớm muộn cũng lệch: đổi tên một giá trị bên proto mà quên bên Python, mapper sẽ
ném KeyError giữa một request thật thay vì báo lúc build. Test này biến comment
đó thành thứ chạy được.
"""
import unittest

from app.api.grpc.generated_stubs import STUBS_READY, get_stub
from app.core.enums import (
    ArbitrationVerdict,
    DocumentFormat,
    ForecastDataSource,
    FraudReason,
    IngestStatus,
    OccupancyStatus,
)

# [MUST] Thêm enum mới vào đây khi thêm domain mới — nếu không, enum đó không
# được canh và sẽ lệch với proto trong im lặng.
MOI_ENUM = (
    ArbitrationVerdict,
    DocumentFormat,
    ForecastDataSource,
    FraudReason,
    IngestStatus,
    OccupancyStatus,
)

# Enum CỐ Ý không có bản sao bên proto. Phải liệt kê ra đây chứ không im lặng
# bỏ qua: bắt người thêm enum mới phải chọn một trong hai — hoặc cho canh, hoặc
# khai rõ là không cần canh kèm lý do.
KHONG_CO_TRONG_PROTO = {
    # Từ vựng loại xe thuộc bảng `parking.vehicle_types` bên backend. Proto để
    # `string` để không tạo nguồn sự thật thứ hai đá nhau với DB.
    "VehicleType",
}


@unittest.skipUnless(STUBS_READY, "Chưa sinh stub — chạy app/script/compile_proto.py")
class EnumMatchesProtoTest(unittest.TestCase):
    def _assert_khop(self, py_enum, proto_enum, ten_proto):
        proto_names = set(proto_enum.keys())
        for member in py_enum:
            self.assertIn(
                member.value,
                proto_names,
                f"'{member.value}' có trong {py_enum.__name__} của Python nhưng "
                f"KHÔNG có trong enum {ten_proto} của proto",
            )

    def test_fraud_reason_khop_mismatch_reason(self):
        pb2, _ = get_stub("vision_service")
        self._assert_khop(FraudReason, pb2.MismatchReason, "MismatchReason")

    def test_occupancy_status_khop(self):
        pb2, _ = get_stub("forecast_service")
        self._assert_khop(OccupancyStatus, pb2.OccupancyStatus, "OccupancyStatus")

    def test_forecast_data_source_khop(self):
        pb2, _ = get_stub("forecast_service")
        self._assert_khop(ForecastDataSource, pb2.ForecastDataSource, "ForecastDataSource")

    def test_arbitration_verdict_khop(self):
        pb2, _ = get_stub("copilot_service")
        self._assert_khop(ArbitrationVerdict, pb2.ArbitrationVerdict, "ArbitrationVerdict")

    def test_document_format_khop(self):
        pb2, _ = get_stub("knowledge_service")
        self._assert_khop(DocumentFormat, pb2.DocumentFormat, "DocumentFormat")

    def test_ingest_status_khop(self):
        pb2, _ = get_stub("knowledge_service")
        self._assert_khop(IngestStatus, pb2.IngestStatus, "IngestStatus")

    def test_gia_tri_unspecified_khong_lot_vao_enum_python(self):
        """`*_UNSPECIFIED = 0` là sentinel của proto, không phải trạng thái nghiệp
        vụ — lọt vào enum Python là dấu hiệu chép máy móc."""
        for py_enum in MOI_ENUM:
            for member in py_enum:
                self.assertNotIn("UNSPECIFIED", member.value)

    def test_moi_enum_deu_duoc_canh(self):
        """Chốt chặn cho chính file test này.

        Thêm enum mới vào `core/enums.py` mà quên thêm vào `MOI_ENUM` thì enum
        đó lệch với proto trong im lặng — đúng kiểu hỏng mà test này sinh ra để
        chặn. Đếm ở đây để việc quên trở thành lỗi đỏ.
        """
        import inspect
        from enum import Enum

        from app.core import enums as module_enums

        khai_trong_code = {
            ten for ten, obj in inspect.getmembers(module_enums, inspect.isclass)
            if issubclass(obj, Enum) and obj is not Enum and obj.__module__ == module_enums.__name__
        }
        duoc_canh = {e.__name__ for e in MOI_ENUM}
        self.assertEqual(
            khai_trong_code,
            duoc_canh | KHONG_CO_TRONG_PROTO,
            "Enum khai trong core/enums.py nhưng chưa quyết: đưa vào MOI_ENUM để "
            "được canh khớp proto, hoặc vào KHONG_CO_TRONG_PROTO kèm lý do.",
        )

    def test_hai_danh_sach_khong_chong_nhau(self):
        """Một enum không thể vừa được canh vừa khai là không cần canh."""
        self.assertEqual(
            set(),
            {e.__name__ for e in MOI_ENUM} & KHONG_CO_TRONG_PROTO,
        )


if __name__ == "__main__":
    unittest.main()
