"""Handler cho `grpc.health.v1.Health` — Docker/k8s probe cổng gRPC bằng đây.

Chỉ báo tiến trình còn phục vụ. KHÔNG cần kiểm tra model ở đây: `grpc_server.py`
nạp model XONG rồi mới mở cổng, nên cổng 50051 trả lời được đã hàm ý model sẵn
sàng.
"""
from app.api.grpc.generated_stubs import get_stub

_pb2, _pb2_grpc = get_stub("health_service")

_SERVING = _pb2.HealthCheckResponse.ServingStatus.SERVING
_SERVICE_UNKNOWN = _pb2.HealthCheckResponse.ServingStatus.SERVICE_UNKNOWN

# Tên service (theo proto, đầy đủ package) mà server này phục vụ.
_KNOWN_SERVICES = frozenset({
    "",  # rỗng = hỏi toàn server
    "iplms.ai.vision.v1.VisionService",
    "iplms.ai.copilot.v1.CopilotService",
    "iplms.ai.forecast.v1.ForecastService",
    "iplms.ai.knowledge.v1.KnowledgeService",
    "iplms.ai.knowledge.v1.KnowledgeEvalService",
    "iplms.ai.dataset.v1.DatasetService",
})


class HealthHandler(_pb2_grpc.HealthServicer):
    async def Check(self, request, context):
        status = _SERVING if request.service in _KNOWN_SERVICES else _SERVICE_UNKNOWN
        return _pb2.HealthCheckResponse(status=status)
