from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple


DEFAULT_HIDDEN_FIELDS = (
    "password",
    "password_confirmation",
    "access_token",
    "secret_key",
    "token",
    "access_key",
)


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _parse_csv(value: Optional[str], default: Sequence[str]) -> Tuple[str, ...]:
    if value is None:
        return tuple(default)

    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class UnderstandConfig:
    token: Optional[str] = None
    enabled: bool = True
    api_url: str = "https://api.understand.io"
    handler: str = "sync"
    project_root: Path = field(default_factory=Path.cwd)
    environment: Optional[str] = None
    sql_enabled: bool = True
    sql_bindings: bool = False
    query_string_enabled: bool = True
    request_body_enabled: bool = True
    hidden_fields: Tuple[str, ...] = DEFAULT_HIDDEN_FIELDS
    ignored_logs: Tuple[str, ...] = ()
    log_filter: Optional[Callable[[str, object, object], bool]] = None
    timeout: float = 5.0
    stack_trace_limit: int = 100
    ssl_ca_bundle: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", Path(self.project_root))
        object.__setattr__(self, "hidden_fields", tuple(self.hidden_fields))
        object.__setattr__(self, "ignored_logs", tuple(self.ignored_logs))

    @classmethod
    def from_env(cls, project_root: Optional[Path] = None) -> "UnderstandConfig":
        request_body_value = os.environ.get("UNDERSTAND_REQUEST_BODY")
        if request_body_value is None:
            request_body_value = os.environ.get("UNDERSTAND_POST_DATA")

        return cls(
            token=os.environ.get("UNDERSTAND_TOKEN"),
            enabled=_parse_bool(os.environ.get("UNDERSTAND_ENABLED"), True),
            api_url=os.environ.get("UNDERSTAND_API_URL", "https://api.understand.io"),
            handler=os.environ.get("UNDERSTAND_HANDLER", "sync"),
            project_root=project_root if project_root is not None else Path.cwd(),
            environment=os.environ.get("UNDERSTAND_ENV"),
            sql_enabled=_parse_bool(os.environ.get("UNDERSTAND_SQL"), True),
            sql_bindings=_parse_bool(os.environ.get("UNDERSTAND_SQL_BINDINGS"), False),
            query_string_enabled=_parse_bool(os.environ.get("UNDERSTAND_QUERY_STRING"), True),
            request_body_enabled=_parse_bool(request_body_value, True),
            hidden_fields=_parse_csv(
                os.environ.get("UNDERSTAND_HIDDEN_REQUEST_FIELDS"),
                DEFAULT_HIDDEN_FIELDS,
            ),
            ssl_ca_bundle=os.environ.get("UNDERSTAND_SSL_CA_BUNDLE"),
        )
