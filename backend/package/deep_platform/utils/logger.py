import logging
import os
import sys

_FORMAT = "%(asctime)s %(levelname)-5s %(message)s"
_DATEFMT = "%H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """自带 stdout handler 的 logger, 不依赖 uvicorn/arq 的日志配置。
    级别可用环境变量 LOG_LEVEL 覆盖 (默认 INFO)。"""
    lg = logging.getLogger(name)
    if not lg.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
        lg.addHandler(h)
    lg.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    lg.propagate = False
    return lg
