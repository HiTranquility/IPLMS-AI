"""Mapper DTO ↔ protobuf của domain Vision.

Đây là chỗ dễ vỡ âm thầm nhất: mapper tra enum bằng CHUỖI
(`MismatchReason.Value(...)`), nên sai chính tả một giá trị là ném lỗi giữa
request thật chứ không phải lúc build.
"""
import unittest

from app.api.grpc.generated_stubs import STUBS_READY, get_stub
from app.core.enums import FraudReason
from app.core.vision.dtos.vision_dto import PlateResult, VehicleMatchResult


@unittest.skipUnless(STUBS_READY, "Chưa sinh stub — chạy app/script/compile_proto.py")
class VisionMapperTest(unittest.TestCase):
    def setUp(self):
        from app.api.grpc.mappers import vision_mapper

        self.mapper = vision_mapper
        self.pb2, _ = get_stub("vision_service")

    def _plate_result(self, **overrides) -> PlateResult:
        data = dict(
            plate_number="51F-178.12",
            crop_image_url="/static/cropped/51F-17812_evt_x_crop.jpg",
            event_id="evt_x",
            timestamp="2026-09-09T00:00:00+00:00",
            lane_id="gate_in_01",
            vehicle_type="car_sedan",
            confidence=0.95,
            process_time=0.8,
            crop_bytes=b"\xff\xd8\xff",
        )
        data.update(overrides)
        return PlateResult(**data)

    def test_map_du_field_sang_response(self):
        res = self.mapper.to_recognize_plate_response(self._plate_result(), 812.5)
        self.assertEqual(res.plate_number, "51F-178.12")
        self.assertEqual(res.vehicle_type, "car_sedan")
        self.assertAlmostEqual(res.process_time_ms, 812.5, places=1)

    def test_crop_bytes_di_len_day(self):
        """Backend cần bytes này để đẩy lên kho lưu trữ bền — thiếu là ảnh chỉ
        còn nằm trên ổ đĩa tạm của pod và mất khi restart."""
        res = self.mapper.to_recognize_plate_response(self._plate_result(), 1.0)
        self.assertEqual(res.crop_image, b"\xff\xd8\xff")

    def test_thieu_crop_bytes_thi_ra_chuoi_rong_chu_khong_no(self):
        res = self.mapper.to_recognize_plate_response(self._plate_result(crop_bytes=None), 1.0)
        self.assertEqual(res.crop_image, b"")

    def test_confidence_none_ve_0_chu_khong_no(self):
        res = self.mapper.to_recognize_plate_response(self._plate_result(confidence=None), 1.0)
        self.assertEqual(res.confidence, 0.0)

    def test_vehicle_type_none_ve_chuoi_rong(self):
        res = self.mapper.to_recognize_plate_response(self._plate_result(vehicle_type=None), 1.0)
        self.assertEqual(res.vehicle_type, "")

    def test_mismatch_reason_map_sang_dung_enum(self):
        result = VehicleMatchResult(
            is_matched=False,
            similarity_score=0.35,
            mismatch_reason=FraudReason.VEHICLE_TYPE_MISMATCH,
        )
        res = self.mapper.to_verify_vehicle_match_response(result)
        self.assertEqual(
            self.pb2.MismatchReason.Name(res.mismatch_reason),
            "VEHICLE_TYPE_MISMATCH",
        )
        self.assertFalse(res.is_matched)

    def test_map_request_lay_dung_field_tu_message(self):
        message = self.pb2.RecognizePlateRequest(
            image_data=b"anh-gia", lane_id="gate_out_02", classify_vehicle=False
        )
        command = self.mapper.to_recognize_plate_command(message)
        self.assertEqual(command.image_data, b"anh-gia")
        self.assertEqual(command.lane_id, "gate_out_02")
        self.assertFalse(command.classify_vehicle)

    def test_lane_id_rong_ve_none_de_service_dung_mac_dinh(self):
        message = self.pb2.RecognizePlateRequest(image_data=b"x", lane_id="", classify_vehicle=True)
        self.assertIsNone(self.mapper.to_recognize_plate_command(message).lane_id)


if __name__ == "__main__":
    unittest.main()
