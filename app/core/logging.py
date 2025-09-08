import logging
import os
from typing import Any, Dict


def configure_logging() -> None:
    level = logging.DEBUG if os.getenv("APP_ENV", "dev") == "dev" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
