"""
Logging configuration for the application.
"""

import logging
import sys


def setup_logging(level: int = logging.INFO):
    """
    Configure root logger with a clean format and reduce noise from
    third-party libraries.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce verbosity of Google API client discovery logging
    logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

    # Reduce SQLAlchemy engine noise (set to DEBUG if you need SQL traces)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
