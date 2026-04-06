import logging
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

class IndustryLogger:
    """
    Structured logger that simulates industry practices.
    Logs to both console and a file in JSON format.
    """
    def __init__(self, name: str = "AI-Lab-Agent", log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        # Avoid duplicated handlers when uvicorn auto-reloads modules.
        if self.logger.handlers:
            self.logger.handlers.clear()

        self._tz = timezone(timedelta(hours=7), name="GMT+7")
        src_root = Path(__file__).resolve().parents[1]
        self.log_dir = (src_root / log_dir).resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # One file per server run/session, named by local GMT+7 timestamp.
        started_at = datetime.now(self._tz)
        self.log_file = self.log_dir / f"{started_at.strftime('%Y%m%d_%H%M%S')}_gmt7.log"

        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(message)s"))

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(message)s"))

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _now_gmt7(self) -> str:
        return datetime.now(self._tz).strftime("%Y-%m-%d %H:%M:%S %Z")

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs an event in readable text format with pretty JSON payload."""
        payload = {
            "timestamp": self._now_gmt7(),
            "event": event_type,
            "data": data
        }
        formatted = (
            f"[{payload['timestamp']}] EVENT: {event_type}\n"
            f"DATA:\n{json.dumps(data, ensure_ascii=False, indent=2)}\n"
            f"{'-' * 88}"
        )
        self.logger.info(formatted)

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str, exc_info=True):
        self.logger.error(msg, exc_info=exc_info)

# Global logger instance
logger = IndustryLogger()
