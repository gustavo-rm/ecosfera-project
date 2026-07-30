"""Logging estruturado (structlog). JSON em staging/prod, legível em dev.

Correlação por trace_id fica pronta para o Inc 0 (observabilidade)."""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.typing import Processor

# Bibliotecas de terceiros que logam em INFO por passo de simulação. Sem isto o
# Mesa emite uma linha por tick de ecologia, afogando o log estruturado.
# O logger do Mesa se chama "MESA" (maiúsculo), não "mesa".
_NOISY_LIBRARIES = ("MESA",)


def configure_logging(*, level: str = "INFO", json_logs: bool = False) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    for library in _NOISY_LIBRARIES:
        logging.getLogger(library).setLevel(logging.WARNING)
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    processors.append(
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level) if isinstance(level, str) else level
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
