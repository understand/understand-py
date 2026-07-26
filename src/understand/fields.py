from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import platform
import sys
from typing import Any, Callable, Dict, Mapping, Optional

from .collector import DataCollector
from .config import UnderstandConfig
from .tokens import TokenProvider


@dataclass
class RequestContext:
    path: Optional[str] = None
    method: Optional[str] = None
    query: Mapping[str, Any] = field(default_factory=dict)
    body: Mapping[str, Any] = field(default_factory=dict)
    client_ip: Optional[str] = None
    server_ip: Optional[str] = None
    user_agent: Optional[str] = None
    host: Optional[str] = None
    origin: Optional[str] = None
    session_id: Optional[str] = None
    session: Mapping[str, Any] = field(default_factory=dict)
    user_id: Optional[Any] = None
    route_name: Optional[str] = None


class FieldProvider:
    def __init__(
        self,
        config: Optional[UnderstandConfig] = None,
        token_provider: Optional[TokenProvider] = None,
        data_collector: Optional[DataCollector] = None,
    ) -> None:
        self.config = config or UnderstandConfig()
        self.token_provider = token_provider or TokenProvider()
        self.data_collector = data_collector or DataCollector()
        self.request_context: Optional[RequestContext] = None
        self._providers: Dict[str, Callable[..., Any]] = {}

    def extend(self, name: str, provider: Callable[..., Any]) -> None:
        self._providers[name] = provider

    def __getattr__(self, name: str) -> Any:
        if name in self._providers:
            return self._providers[name]
        raise AttributeError(name)

    def set_request_context(self, request_context: Optional[RequestContext]) -> None:
        self.request_context = request_context

    def resolve_values(
        self,
        callbacks: Mapping[str, Callable[[Mapping[str, Any]], Any]],
        log: Mapping[str, Any],
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for field_name, callback in callbacks.items():
            try:
                data[field_name] = callback(log)
            except Exception:
                data[field_name] = None
        return data

    def get_session_id(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        if not self.request_context or not self.request_context.session_id:
            return None
        return hashlib.sha1(self.request_context.session_id.encode("utf-8")).hexdigest()

    def get_request_id(self, _log: Optional[Mapping[str, Any]] = None) -> str:
        return self.token_provider.get_token()

    def get_process_identifier(self, _log: Optional[Mapping[str, Any]] = None) -> str:
        return self.get_request_id()

    def get_user_id(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[Any]:
        if not self.request_context:
            return None
        return self.request_context.user_id

    def get_environment(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        return self.config.environment

    def get_url(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        if not self.request_context or self.request_context.path is None:
            return None
        path = self.request_context.path
        return path if path.startswith("/") else "/" + path

    def get_request_method(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        if not self.request_context:
            return None
        return self.request_context.method

    def get_route_name(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        if not self.request_context:
            return None
        return self.request_context.route_name

    def get_from_session(self, key: str) -> Optional[Any]:
        if not self.request_context:
            return None
        return self.request_context.session.get(key)

    def get_query_string_array(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.config.query_string_enabled:
            return None
        if not self.request_context:
            return None
        return self._parse_request_mapping(self.request_context.query)

    def get_request_body_data(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.config.request_body_enabled:
            return None
        if not self.request_context:
            return None
        if self.request_context.method and self.request_context.method.upper() in {"GET", "HEAD"}:
            return None
        return self._parse_request_mapping(self.request_context.body)

    def get_post_data_array(self, log: Optional[Mapping[str, Any]] = None) -> Optional[Dict[str, Any]]:
        return self.get_request_body_data(log)

    def get_client_ip(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        return self.request_context.client_ip if self.request_context else None

    def get_server_ip(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        return self.request_context.server_ip if self.request_context else None

    def get_client_user_agent(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        return self.request_context.user_agent if self.request_context else None

    def get_host(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        return self.request_context.host if self.request_context else None

    def get_origin(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        return self.request_context.origin if self.request_context else None

    def get_python_version(self, _log: Optional[Mapping[str, Any]] = None) -> str:
        return platform.python_version()

    def get_logger_version(self, _log: Optional[Mapping[str, Any]] = None) -> str:
        from . import __version__

        return __version__

    def get_console(self, _log: Optional[Mapping[str, Any]] = None) -> bool:
        return True

    def get_command(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        return " ".join(sys.argv) if sys.argv else None

    def get_artisan_command_name(self, log: Optional[Mapping[str, Any]] = None) -> Optional[str]:
        return self.get_command(log)

    def get_sql_queries(self, _log: Optional[Mapping[str, Any]] = None) -> Optional[Any]:
        if not self.config.sql_enabled:
            return None
        queries = self.data_collector.get_by_key("sql_queries")
        if not queries:
            return None

        result = []
        for query in queries:
            query_dict = dict(query)
            bindings = list(query_dict.pop("bindings", []))
            if self.config.sql_bindings:
                query_dict["query"] = self._merge_bindings(str(query_dict.get("query", "")), bindings)
            result.append(query_dict)
        return result

    def get_group_id(self, log: Mapping[str, Any]) -> str:
        parts = []
        for field_name in ("class", "file", "line", "code"):
            value = log.get(field_name)
            if field_name == "code" and (not value or value == "0"):
                continue
            parts.append("" if value is None else str(value))
        return hashlib.sha1("#".join(parts).encode("utf-8")).hexdigest()

    def _parse_request_mapping(self, mapping: Mapping[str, Any]) -> Dict[str, Any]:
        parsed: Dict[str, Any] = {}
        for key, value in mapping.items():
            try:
                parsed[key] = self._parse_request_field_value(key, value)
            except Exception:
                parsed[key] = "[handler error]"
        return parsed

    def _parse_request_field_value(self, key: str, value: Any) -> Any:
        if key in self.config.hidden_fields:
            return "[value hidden]"
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, (list, tuple, dict, set)):
            return repr(value)
        return value.__class__.__name__

    def _merge_bindings(self, query: str, bindings: Any) -> str:
        for value in bindings:
            if isinstance(value, datetime):
                binding = value.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(value, bool):
                binding = "1" if value else "0"
            else:
                binding = str(value)
            query = query.replace("?", binding, 1)
        return query
