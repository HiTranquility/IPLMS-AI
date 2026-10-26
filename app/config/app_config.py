"""Config tổng — gom mọi nhóm config nhỏ, cache lại 1 instance cho cả tiến trình."""
from functools import lru_cache

from app.config.console_config import ConsoleConfig
from app.config.datalake_config import DatalakeConfig
from app.config.embedding_config import EmbeddingConfig
from app.config.eval_config import EvalConfig
from app.config.llm_config import LlmConfig
from app.config.logging_config import LoggingConfig
from app.config.model_registry_config import ModelRegistryConfig
from app.config.object_storage_config import ObjectStorageConfig
from app.config.runtime_override_config import apply_runtime_overrides
from app.config.server_config import ServerConfig
from app.config.telemetry_config import TelemetryConfig
from app.config.vision_config import VisionConfig
from app.config.workflow_config import WorkflowConfig


class AppConfig:
    def __init__(self) -> None:
        self.server = ServerConfig()
        self.vision = VisionConfig()
        self.llm = LlmConfig()
        self.embedding = EmbeddingConfig()
        self.datalake = DatalakeConfig()
        self.logging = LoggingConfig()
        self.model_registry = ModelRegistryConfig()
        self.object_storage = ObjectStorageConfig()
        self.workflow = WorkflowConfig()
        self.eval = EvalConfig()
        self.console = ConsoleConfig()
        self.telemetry = TelemetryConfig()
        self.reload_runtime_overrides()

    def reload_runtime_overrides(self) -> None:
        """Áp cấu hình đổi ở trang Settings (var/runtime_settings.json)."""
        apply_runtime_overrides(self)


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
