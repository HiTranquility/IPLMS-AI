"""Handler cho `grpc.health.v1.Health` — Docker/k8s probe cổng gRPC bằng đây.

Hỏi toàn server (`service=""`) chỉ báo tiến trình còn phục vụ. KHÔNG kiểm model:
`grpc_server.py` nạp model XONG rồi mới mở cổng (production).

ISSUE-013: hỏi TỪNG service thì service cần mô hình ngôn ngữ / embedding báo
`NOT_SERVING` khi chưa cấu hình (thiếu cả key lẫn base_url) — trang "Sức khoẻ AI"
dựa vào đây để nói thật "chưa cấu hình", không phải đợi người dùng chat mới biết.
"""
from app.api.grpc.generated_stubs import get_stub
from app.config import get_config

_pb2, _pb2_grpc = get_stub("health_service")

_SERVING = _pb2.HealthCheckResponse.ServingStatus.SERVING
_SERVICE_UNKNOWN = _pb2.HealthCheckResponse.ServingStatus.SERVICE_UNKNOWN
_NOT_SERVING = _pb2.HealthCheckResponse.ServingStatus.NOT_SERVING

# Tên service (theo proto, đầy đủ package) mà server này phục vụ.
_KNOWN_SERVICES = frozenset({
    "",  # rỗng = hỏi toàn server
    "iplms.ai.vision.v1.VisionService",
    "iplms.ai.copilot.v1.CopilotService",
    "iplms.ai.forecast.v1.ForecastService",
    "iplms.ai.knowledge.v1.KnowledgeService",
    "iplms.ai.knowledge.v1.KnowledgeEvalService",
    "iplms.ai.dataset.v1.DatasetService",
    "iplms.ai.modelpolicy.v1.ModelPolicyService",
})


_NEEDS_LLM = frozenset({
    "iplms.ai.copilot.v1.CopilotService",
    "iplms.ai.knowledge.v1.KnowledgeEvalService",
})
_NEEDS_EMBEDDING = frozenset({"iplms.ai.knowledge.v1.KnowledgeService"})


def _llm_configured() -> bool:
    llm = get_config().llm
    return bool(llm.llm_api_key or llm.llm_base_url)


def _embedding_configured() -> bool:
    config = get_config()
    return bool(config.llm.llm_api_key or config.embedding.base_url)


class HealthHandler(_pb2_grpc.HealthServicer):
    async def Check(self, request, context):
        service = request.service
        if service not in _KNOWN_SERVICES:
            status = _SERVICE_UNKNOWN
        elif service in _NEEDS_LLM and not _llm_configured():
            status = _NOT_SERVING
        elif service in _NEEDS_EMBEDDING and not _embedding_configured():
            status = _NOT_SERVING
        else:
            status = _SERVING
        return _pb2.HealthCheckResponse(status=status)
