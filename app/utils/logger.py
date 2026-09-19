"""Logger dùng chung, cấu hình lấy từ `app.config.logging_config.LoggingConfig`."""
import logging
import sys

from app.config import get_config
from app.utils.console import enable_utf8_stdio


def setup_logger() -> logging.Logger:
    enable_utf8_stdio()
    cfg = get_config().logging
    instance = logging.getLogger(cfg.name)
    if not instance.handlers:
        instance.setLevel(cfg.level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(cfg.level)
        handler.setFormatter(logging.Formatter(cfg.format, datefmt=cfg.datefmt))
        instance.addHandler(handler)
    return instance


logger = setup_logger()
