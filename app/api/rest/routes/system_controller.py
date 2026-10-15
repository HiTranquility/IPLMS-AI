"""REST route cho System Diagnostics & Health Inspection."""
import os
from typing import Any, Dict
from fastapi import APIRouter

from app.config import get_config

router = APIRouter(prefix="/system", tags=["System Diagnostics"])


@router.get("/info")
async def get_system_info() -> Dict[str, Any]:
    """Trả về chi tiết trạng thái môi trường, model AI và cấu hình runtime."""
    cfg = get_config()
    
    # 1. Kiểm tra YOLO weights
    yolo_exists = os.path.exists(cfg.vision.yolo_model_path)
    yolo_size_mb = round(os.path.getsize(cfg.vision.yolo_model_path) / (1024 * 1024), 2) if yolo_exists else 0.0

    # 2. Kiểm tra EasyOCR cache
    easyocr_dir = os.environ.get("EASYOCR_MODULE_PATH", "var/easyocr-cache")
    easyocr_model_dir = os.path.join(easyocr_dir, "model") if os.path.isabs(easyocr_dir) else os.path.join(os.getcwd(), easyocr_dir, "model")
    easyocr_exists = os.path.exists(easyocr_model_dir) and len(os.listdir(easyocr_model_dir)) > 0 if os.path.exists(easyocr_model_dir) else False

    # 3. Kiểm tra PyTorch
    torch_version = "unknown"
    cuda_available = False
    device_name = "CPU"
    try:
        import torch
        torch_version = getattr(torch, "__version__", "unknown")
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    # 4. Che mật khẩu trong database URL
    db_url = cfg.llm.database_url
    safe_db_url = db_url
    if "@" in db_url:
        prefix, host = db_url.split("@", 1)
        scheme, user_part = prefix.split("://", 1)
        safe_db_url = f"{scheme}://***:***@{host}"

    return {
        "service": {
            "name": "iplms-ai",
            "version": "0.3.0",
            "environment": os.environ.get("ENV", "development"),
            "device": cfg.vision.device,
        },
        "vision": {
            "yolo_model_path": cfg.vision.yolo_model_path,
            "yolo_exists": yolo_exists,
            "yolo_size_mb": yolo_size_mb,
            "yolo_version": cfg.vision.yolo_model_version,
            "ocr_languages": cfg.vision.ocr_language_list,
            "easyocr_cached": easyocr_exists,
            "easyocr_dir": easyocr_dir,
            "vehicle_classifier": cfg.vision.vehicle_model,
        },
        "torch": {
            "version": torch_version,
            "cuda_available": cuda_available,
            "device_name": device_name,
        },
        "copilot": {
            "embedding_model": cfg.embedding.model,
            "embedding_dimensions": cfg.embedding.dimensions,
            "llm_model": cfg.llm.llm_model,
            "has_llm_api_key": bool(cfg.llm.llm_api_key),
            "database_url": safe_db_url,
            "workflow_enabled": cfg.workflow.enabled,
        },
        "server": {
            "fastapi_port": cfg.server.fastapi_port,
            "grpc_port": cfg.server.grpc_port,
        },
        "architecture_rules": [
            "api/ -> core/ -> infra/ (Phụ thuộc một chiều duy nhất)",
            "Hai cổng, một đường: REST & gRPC dùng chung core services",
            "Thà lỗi hơn bịa (ADR-0008): Từ chối trả số giả khi chưa có model thật",
            "Lazy-load model weights với thread locking",
        ]
    }
