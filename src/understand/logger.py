import time
from typing import Any, Dict, Mapping, Optional

from .collector import DataCollector
from .config import UnderstandConfig
from .encoder import ExceptionEncoder
from .fields import FieldProvider
from .handlers import AsyncHandler, BaseHandler, SyncHandler
from .tokens import TokenProvider


class UnderstandLogger:
    def __init__(
        self,
        config: Optional[UnderstandConfig] = None,
        field_provider: Optional[FieldProvider] = None,
        handler: Optional[BaseHandler] = None,
        encoder: Optional[ExceptionEncoder] = None,
    ) -> None:
        self.config = config or UnderstandConfig()
        self.field_provider = field_provider or FieldProvider(
            config=self.config,
            token_provider=TokenProvider(),
            data_collector=DataCollector(),
        )
        self.handler = handler or self._handler_from_config(self.config)
        if getattr(self.handler, "config", None) is None:
            self.handler.config = self.config
        else:
            self.handler.config = self.config
        self.encoder = encoder or ExceptionEncoder(self.config)

    @classmethod
    def from_config(
        cls,
        config: Optional[UnderstandConfig] = None,
        handler: Optional[BaseHandler] = None,
    ) -> "UnderstandLogger":
        return cls(config=config or UnderstandConfig.from_env(), handler=handler)

    def log(
        self,
        message: Any,
        level: str = "error",
        context: Optional[Mapping[str, Any]] = None,
        additional: Optional[Mapping[str, Any]] = None,
        custom_fields: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        if not self._can_deliver(level, message, context):
            return False

        log = dict(message) if isinstance(message, Mapping) else {"message": message}
        log["message"] = self._format_message(log.get("message"))
        log["level"] = level
        log.setdefault("tags", ["python_log"])
        if context:
            log["context"] = dict(context)

        event = self._prepare(log, additional or self.event_meta_fields(), custom_fields or {})
        return self._send(event)

    def error(self, message: Any, level: str = "error", context: Optional[Mapping[str, Any]] = None) -> Any:
        return self.log(message, level=level, context=context)

    def reset_context(self) -> None:
        self.field_provider.token_provider.generate()
        self.field_provider.data_collector.reset()

    def exception(
        self,
        exception: BaseException,
        level: str = "error",
        context: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        if not self._can_deliver(level, exception, context):
            return False

        log = self.encoder.exception_to_dict(exception)
        log["level"] = level
        log["tags"] = ["py_error_log"]
        if context:
            log["context"] = dict(context)
        event = self._prepare(log, self.error_meta_fields(), {})
        return self._send(event)

    def event_meta_fields(self) -> Dict[str, Any]:
        return {
            "session_id": self.field_provider.get_session_id,
            "request_id": self.field_provider.get_request_id,
            "user_id": self.field_provider.get_user_id,
            "env": self.field_provider.get_environment,
            "url": self.field_provider.get_url,
            "route": self.field_provider.get_route_name,
            "method": self.field_provider.get_request_method,
            "client_ip": self.field_provider.get_client_ip,
            "server_ip": self.field_provider.get_server_ip,
        }

    def error_meta_fields(self) -> Dict[str, Any]:
        return {
            "session_id": self.field_provider.get_session_id,
            "request_id": self.field_provider.get_request_id,
            "group_id": self.field_provider.get_group_id,
            "user_id": self.field_provider.get_user_id,
            "env": self.field_provider.get_environment,
            "url": self.field_provider.get_url,
            "route": self.field_provider.get_route_name,
            "method": self.field_provider.get_request_method,
            "query_string_data": self.field_provider.get_query_string_array,
            "request_body_data": self.field_provider.get_request_body_data,
            "client_ip": self.field_provider.get_client_ip,
            "server_ip": self.field_provider.get_server_ip,
            "user_agent": self.field_provider.get_client_user_agent,
            "host": self.field_provider.get_host,
            "origin": self.field_provider.get_origin,
            "python_version": self.field_provider.get_python_version,
            "sql_queries": self.field_provider.get_sql_queries,
            "console": self.field_provider.get_console,
            "command": self.field_provider.get_command,
            "logger_version": self.field_provider.get_logger_version,
        }

    def _prepare(
        self,
        log: Dict[str, Any],
        additional: Mapping[str, Any],
        custom_fields: Mapping[str, Any],
    ) -> Dict[str, Any]:
        data = self.field_provider.resolve_values(additional, log)
        if custom_fields:
            data["custom"] = self.field_provider.resolve_values(custom_fields, log)
        event = dict(data)
        event.update(log)
        event.setdefault("timestamp", round(time.time() * 1000))
        return event

    def _send(self, event: Dict[str, Any]) -> Any:
        try:
            return self.handler.handle(event)
        except Exception:
            return False

    def _can_deliver(self, level: str, message: Any, context: Optional[Mapping[str, Any]]) -> bool:
        if not self.config.enabled:
            return False
        if level in self.config.ignored_logs:
            return False
        if self.config.log_filter and self.config.log_filter(level, message, context or {}):
            return False
        return True

    def _format_message(self, message: Any) -> str:
        if isinstance(message, bool):
            return "1" if message else "0"
        return str(message)

    def _handler_from_config(self, config: UnderstandConfig) -> BaseHandler:
        if config.handler == "async":
            return AsyncHandler(config)
        if config.handler == "sync":
            return SyncHandler(config)
        raise ValueError("understand handler misconfiguration: " + str(config.handler))
