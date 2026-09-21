"""Entrypoint gRPC server (mặc định cổng 50051) — NestJS backend gọi vào đây.

Chạy: `python -m app.grpc_server`
Điều kiện: đã sinh stub bằng `python app/script/compile_proto.py`.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor

from grpc import aio

from app.api.grpc.generated_stubs import get_stub, require_stubs
from app.api.grpc.interceptors import build_interceptors
from app.config import get_config
from app.utils.logger import logger

# Thêm proto service mới = thêm ĐÚNG 1 dòng ở đây (và 1 handler).
# (tên file proto, tên hàm add_*_to_server, đường import handler, nhãn log)
SERVICE_REGISTRY = (
    ("vision_service", "add_VisionServiceServicer_to_server", "VisionHandler", "ANPR & Anti-Fraud"),
    ("copilot_service", "add_CopilotServiceServicer_to_server", "CopilotHandler", "RAG & Dispute"),
    ("knowledge_service", "add_KnowledgeServiceServicer_to_server", "KnowledgeHandler", "Knowledge ingestion"),
    ("forecast_service", "add_ForecastServiceServicer_to_server", "ForecastHandler", "Occupancy & Tariff"),
    ("health_service", "add_HealthServicer_to_server", "HealthHandler", "grpc.health.v1"),
)


async def serve() -> None:
    require_stubs(*(proto for proto, *_ in SERVICE_REGISTRY))
    config = get_config().server

    # Handler CPU-bound (YOLO/OCR) chạy qua asyncio.to_thread → executor mặc định
    # chính là nơi grpc_max_workers có tác dụng.
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=config.grpc_max_workers)
    )

    server = aio.server(
        interceptors=build_interceptors(),
        options=[
            ("grpc.max_receive_message_length", config.grpc_max_message_length),
            ("grpc.max_send_message_length", config.grpc_max_message_length),
        ],
    )

    # Import muộn: handler đụng stub ở module level nên phải chắc stub có sẵn.
    from app.api.grpc import handlers as handler_module

    for proto_name, register_fn, handler_name, _label in SERVICE_REGISTRY:
        _, pb2_grpc = get_stub(proto_name)
        getattr(pb2_grpc, register_fn)(getattr(handler_module, handler_name)(), server)

    # Nạp model TRƯỚC khi mở cổng: mở cổng rồi mới nạp nghĩa là loạt request đầu
    # tiên sau mỗi lần restart pod phải đứng chờ 8-10 giây nạp model (hoặc hỏng
    # hẳn nếu chúng ập vào cùng lúc). Trả giá một lần ở đây, ngay chỗ k8s vẫn
    # đang coi pod là chưa sẵn sàng.
    from app.core.vision.engines.anpr_engine import warmup

    if await asyncio.to_thread(warmup):
        logger.info("Model Vision đã nạp xong — sẵn sàng nhận request.")
    else:
        logger.warning("Chưa nạp được OCR reader — RecognizePlate sẽ trả FAILED_PRECONDITION.")

    server.add_insecure_port(f"[::]:{config.grpc_port}")
    await server.start()

    logger.info(f"🚀 IPLMS AI gRPC Server started on port {config.grpc_port}")
    for _proto, _fn, handler_name, label in SERVICE_REGISTRY:
        logger.info(f"   ├─ {handler_name:<16} ({label})")

    try:
        await server.wait_for_termination()
    finally:
        logger.info("Đang dừng gRPC server, chờ tối đa 5 giây cho request đang chạy.")
        await server.stop(grace=5)


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
