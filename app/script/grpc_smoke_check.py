import sys
import os
import grpc
import time
from pathlib import Path

# Thêm thư mục ai/ vào sys.path để import app.* chạy trực tiếp được
AI_ROOT = Path(__file__).resolve().parents[2]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

# Set utf-8 stdout
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.api.grpc.generated_stubs import get_stub

# generated_stubs nạp stub ĐỘNG (quét thư mục generated/), nên lấy qua get_stub
# thay vì import theo tên — thêm proto mới không phải sửa file này.
vision_service_pb2, vision_service_pb2_grpc = get_stub("vision_service")
copilot_service_pb2, copilot_service_pb2_grpc = get_stub("copilot_service")
forecast_service_pb2, forecast_service_pb2_grpc = get_stub("forecast_service")
health_service_pb2, health_service_pb2_grpc = get_stub("health_service")


def expect_unimplemented(label: str, call):
    """Gọi một RPC được kỳ vọng trả UNIMPLEMENTED, và báo ĐỎ nếu nó trả dữ liệu.

    [GOTCHA] Chiều kiểm ngược với phần còn lại của file này. Ba service dưới đây
    (Forecast ×2, Copilot ×2) CỐ Ý chưa triển khai và trả `UNIMPLEMENTED` thay vì
    số bịa. Nếu một ngày chúng trả về dữ liệu mà chưa ai làm model thật, nghĩa là
    hằng số đã bò trở lại — đó mới là lỗi cần hét lên.
    """
    try:
        call()
    except grpc.RpcError as exc:
        if exc.code() == grpc.StatusCode.UNIMPLEMENTED:
            print(f"   [OK] Từ chối đúng: UNIMPLEMENTED")
            print(f"        └─ {exc.details()}")
            return True
        print(f"   [FAIL] Sai mã lỗi: {exc.code()} — {exc.details()}")
        return False
    print(f"   [FAIL] {label} TRẢ VỀ DỮ LIỆU nhưng chưa có model thật — hằng số đã quay lại!")
    return False


def run_tests():
    channel = grpc.insecure_channel("localhost:50051")
    
    print("=" * 70)
    print("[TEST] IPLMS E2E gRPC COMMUNICATION & MULTI-PROTO TEST")
    print("=" * 70)
    
    # TEST 1: VisionService.RecognizePlate
    print("\n[TEST 1] VisionService.RecognizePlate (from vision_service.proto):")
    vision_stub = vision_service_pb2_grpc.VisionServiceStub(channel)
    
    # Generate real license plate image canvas
    import cv2
    import numpy as np
    canvas = np.zeros((300, 500, 3), dtype=np.uint8)
    canvas[:] = (240, 240, 240)
    cv2.rectangle(canvas, (30, 40), (470, 260), (255, 255, 255), -1)
    cv2.rectangle(canvas, (30, 40), (470, 260), (0, 0, 0), 4)
    cv2.putText(canvas, "51H - 988.88", (65, 170), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (10, 10, 10), 4)
    _, encoded = cv2.imencode(".jpg", canvas)
    sample_image_bytes = encoded.tobytes()

    req1 = vision_service_pb2.RecognizePlateRequest(
        image_data=sample_image_bytes,
        lane_id="gate_in_01",
        classify_vehicle=True,
    )
    t0 = time.perf_counter()
    resp1 = vision_stub.RecognizePlate(req1)
    t_elap = (time.perf_counter() - t0) * 1000
    
    print(f"   [OK] Plate Detected:  {resp1.plate_number}")
    print(f"   [OK] Vehicle Type:    {resp1.vehicle_type}")
    print(f"   [OK] Confidence:      {resp1.confidence * 100:.1f}%")
    print(f"   [OK] Server Latency:  {resp1.process_time_ms:.2f}ms (Client RTT: {t_elap:.2f}ms)")
    
    # TEST 2: VisionService.VerifyVehicleMatch
    print("\n[TEST 2] VisionService.VerifyVehicleMatch (Anti-Fraud Check):")
    req2 = vision_service_pb2.VerifyVehicleMatchRequest(
        checkin_crop_url="https://storage.iplms.vn/crops/checkin_51H98888.jpg",
        checkout_crop_url="https://storage.iplms.vn/crops/checkout_51H98888.jpg",
        expected_vehicle_type="car_sedan",
        current_vehicle_type="car_suv",
    )
    resp2 = vision_stub.VerifyVehicleMatch(req2)
    print(f"   [OK] Match Status:    {resp2.is_matched} (False = Fraud Swapped Vehicle Caught)")
    print(f"   [OK] Similarity:      {resp2.similarity_score * 100:.1f}%")
    print(f"   [OK] Fraud Reason:    {vision_service_pb2.MismatchReason.Name(resp2.mismatch_reason)}")
    
    # TEST 3: ForecastService.GetOccupancyForecast
    print("\n[TEST 3] ForecastService.GetOccupancyForecast (from forecast_service.proto):")
    forecast_stub = forecast_service_pb2_grpc.ForecastServiceStub(channel)
    req3 = forecast_service_pb2.OccupancyForecastRequest(
        parking_lot_id="vincom-dong-khoi-p01",
        target_timestamp=int(time.time()),
        forecast_hours=4,
    )
    ok3 = expect_unimplemented(
        "GetOccupancyForecast", lambda: forecast_stub.GetOccupancyForecast(req3)
    )

    print("\n[TEST 3b] ForecastService.GetDynamicTariffRecommendation:")
    req3b = forecast_service_pb2.TariffRecommendationRequest(
        parking_lot_id="vincom-dong-khoi-p01", base_hourly_rate=35000
    )
    ok3b = expect_unimplemented(
        "GetDynamicTariffRecommendation",
        lambda: forecast_stub.GetDynamicTariffRecommendation(req3b),
    )

    # TEST 4: CopilotService.AskQuestion
    print("\n[TEST 4] CopilotService.AskQuestion (from copilot_service.proto):")
    copilot_stub = copilot_service_pb2_grpc.CopilotServiceStub(channel)
    req4 = copilot_service_pb2.AskQuestionRequest(
        query="Nếu tôi bị kẹt ở cổng barie quá 15 phút do lỗi máy quét thì có được bồi thường không?",
        user_id="usr_test_123",
        user_role="member",
        parking_lot_id="vincom-dong-khoi-p01",
    )
    ok4 = expect_unimplemented("AskQuestion", lambda: copilot_stub.AskQuestion(req4))

    # TEST 5: grpc.health.v1.Health -- dung probe ma Docker/k8s goi
    print("\n[TEST 5] Health.Check (from health_service.proto):")
    health_stub = health_service_pb2_grpc.HealthStub(channel)
    resp5 = health_stub.Check(health_service_pb2.HealthCheckRequest(service=""))
    _status = health_service_pb2.HealthCheckResponse.ServingStatus.Name(resp5.status)
    print(f"   [OK] Serving Status:  {_status}")

    print("\n" + "=" * 70)
    if all([ok3, ok3b, ok4]):
        print("[SUCCESS] Vision + Health chay that; Forecast + Copilot tu choi dung cach.")
        print("          Chi ANPR la AI that — 3 service kia cho model, xem ai/README.md.")
    else:
        print("[FAIL] Co service tra du lieu trong khi chua co model that.")
    print("=" * 70)
    return all([ok3, ok3b, ok4])


if __name__ == "__main__":
    raise SystemExit(0 if run_tests() else 1)
