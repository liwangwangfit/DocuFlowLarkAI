"""
日志配置
"""
import sys
from pathlib import Path
from loguru import logger as _logger

from config import LOGS_DIR

# 配置日志
_logger.remove()

# 控制台输出
_console_sink = sys.stdout if getattr(sys, "stdout", None) is not None else None
if _console_sink is not None:
    _logger.add(
        _console_sink,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )

# 文件输出
_logger.add(
    LOGS_DIR / "app.log",
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# 错误日志单独存储
_logger.add(
    LOGS_DIR / "error.log",
    rotation="10 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR"
)


def get_logger(name: str):
    """获取logger实例"""
    return _logger.bind(name=name)
