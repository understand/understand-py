import logging
import sys
from typing import Optional

from ..config import UnderstandConfig
from ..logger import UnderstandLogger


class UnderstandLoggingHandler(logging.Handler):
    def __init__(self, understand_logger: UnderstandLogger, level: int = logging.NOTSET) -> None:
        super().__init__(level)
        self.understand_logger = understand_logger

    @classmethod
    def from_config(cls, config: Optional[UnderstandConfig] = None) -> "UnderstandLoggingHandler":
        return cls(UnderstandLogger.from_config(config or UnderstandConfig.from_env()))

    def emit(self, record: logging.LogRecord) -> None:
        context = {
            "logger_name": record.name,
            "module": record.module,
            "pathname": record.pathname,
            "lineno": record.lineno,
        }
        level = record.levelname.lower()

        exc_info = record.exc_info
        if exc_info is True:
            exc_info = sys.exc_info()

        if exc_info and exc_info[1]:
            self.understand_logger.exception(exc_info[1], level=level, context=context)
            return

        self.understand_logger.log(record.getMessage(), level=level, context=context)
