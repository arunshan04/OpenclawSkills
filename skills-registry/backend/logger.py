import logging
import json
import os
import time
from collections import deque
from datetime import datetime, timezone

# In-memory ring buffer — last 500 log entries served via /logs
_log_buffer: deque = deque(maxlen=500)

# Write log file outside the project directory so watchfiles doesn't pick it up
LOG_FILE = os.environ.get("REGISTRY_LOG_FILE", "/tmp/registry.log")


_STRUCTURED_FIELDS = {
    "event", "tool", "skill_id", "skill_name",
    "params", "result", "error", "execution_ms", "ok",
}


class BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for field in _STRUCTURED_FIELDS:
            if hasattr(record, field):
                entry[field] = getattr(record, field)
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

    # File (written to /tmp to avoid triggering watchfiles reload)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # In-memory buffer for /logs API
    root.addHandler(BufferHandler())

    # Silence noisy internal MCP/uvicorn/watchfiles loggers
    for noisy in ("mcp.server", "uvicorn.access", "uvicorn.error", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_log_buffer() -> list:
    return list(_log_buffer)


def log(name: str) -> logging.Logger:
    return logging.getLogger(name)
