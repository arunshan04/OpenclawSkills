import logging
import json
import time
from collections import deque
from datetime import datetime, timezone

# In-memory ring buffer — last 500 log entries served via /logs
_log_buffer: deque = deque(maxlen=500)


class BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra"):
            entry.update(record.extra)
        _log_buffer.append(entry)


def setup_logging():
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Console
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # File
    file_handler = logging.FileHandler("registry.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # In-memory buffer for /logs API
    root.addHandler(BufferHandler())


def get_log_buffer() -> list:
    return list(_log_buffer)


def log(name: str) -> logging.Logger:
    return logging.getLogger(name)
