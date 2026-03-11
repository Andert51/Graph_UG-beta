"""Centralised logging configuration for GraphUG.

Usage
-----
    from app.utils.logger import get_logger
    log = get_logger(__name__)
    log.debug("parser initialised")

All loggers share the same handlers (stderr + rotating file).  The file is
written to ``~/.graphug/logs/graphug.log``.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path.home() / ".graphug" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_LOG_FILE = _LOG_DIR / "graphug.log"
_FMT = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Root logger for the application — configured once, shared everywhere
_root_logger = logging.getLogger("graphug")
_root_logger.setLevel(logging.DEBUG)

if not _root_logger.handlers:
    # Stderr — INFO and above so production consoles stay clean
    _sh = logging.StreamHandler(sys.stderr)
    _sh.setLevel(logging.INFO)
    _sh.setFormatter(_FMT)
    _root_logger.addHandler(_sh)

    # Rotating file — DEBUG and above for post-mortem analysis
    _fh = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=2 * 1024 * 1024,  # 2 MiB per file
        backupCount=3,
        encoding="utf-8",
    )
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(_FMT)
    _root_logger.addHandler(_fh)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger inheriting GraphUG's handlers.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.
    """
    return _root_logger.getChild(name)
