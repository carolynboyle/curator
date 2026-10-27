"""
contactkit.logger - Logging configuration (fletcher-style).
"""

import json
import logging
import sys
from pathlib import Path


def setup_logger():
    """Set up human-readable and JSON loggers."""
    log_dir = Path.home() / ".local" / "share" / "dev-utils"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("contactkit")
    logger.setLevel(logging.DEBUG)

    # Human-readable log file
    fh = logging.FileHandler(log_dir / "contactkit.log")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(fh)

    # JSON log file
    json_handler = JsonFileHandler(log_dir / "contactkit.json.log")
    json_handler.setLevel(logging.DEBUG)
    logger.addHandler(json_handler)

    # Console output
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    return logger


class JsonFileHandler(logging.Handler):
    """Log handler that writes JSON to file."""

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def emit(self, record):
        """Emit a record as JSON."""
        try:
            log_entry = {
                "timestamp": self.format(record),
                "level": record.levelname,
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_entry["exception"] = self.format(record)

            with open(self.filename, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            self.handleError(record)


logger = setup_logger()
