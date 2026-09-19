"""Config package — luôn lấy config qua `get_config()`, không đọc os.getenv rải rác."""
from app.config.app_config import AppConfig, get_config

__all__ = ["AppConfig", "get_config"]
