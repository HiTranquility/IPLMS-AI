"""Config tổng — gom mọi nhóm config nhỏ, cache lại 1 instance cho cả tiến trình."""
from functools import lru_cache

from app.config.datalake_config import DatalakeConfig
from app.config.embedding_config import EmbeddingConfig
from app.config.llm_config import LlmConfig
from app.config.logging_config import LoggingConfig
from app.config.model_registry_config import ModelRegistryConfig
from app.config.object_storage_config import ObjectStorageConfig
from app.config.server_config import ServerConfig
from app.config.vision_config import VisionConfig


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


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
