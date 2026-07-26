import json
import subprocess
from typing import Any, Callable, Dict, Optional
from urllib import request

from .config import UnderstandConfig


class BaseHandler:
    def __init__(self, config: Optional[UnderstandConfig] = None) -> None:
        self.config = config or UnderstandConfig()

    def handle(self, request_data: Dict[str, Any]) -> Any:
        payload = json.dumps(request_data, default=str)
        response = self.send(payload)
        return self.parse_response(response)

    def send(self, data: str) -> Optional[str]:
        raise NotImplementedError

    def get_endpoint(self) -> str:
        return "/".join([self.config.api_url.rstrip("/"), str(self.config.token or "")])

    def parse_response(self, response: Optional[str]) -> Any:
        if response is None:
            return None
        if response == "":
            return None
        return json.loads(response)


class SyncHandler(BaseHandler):
    def send(self, data: str) -> Optional[str]:
        req = request.Request(
            self.get_endpoint(),
            data=data.encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Understand Python SDK.",
            },
        )
        kwargs = {"timeout": self.config.timeout}
        if self.config.ssl_ca_bundle:
            kwargs["cafile"] = self.config.ssl_ca_bundle
        with request.urlopen(req, **kwargs) as response:
            return response.read().decode("utf-8")


class AsyncHandler(BaseHandler):
    def send(self, data: str) -> None:
        if len(data) >= 2_000_000:
            return None

        subprocess.Popen(
            ["curl", "-X", "POST", "-d", data, self.get_endpoint()],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return None


class CallbackHandler(BaseHandler):
    def __init__(self, callback: Callable[[str], Optional[str]], config: Optional[UnderstandConfig] = None) -> None:
        super().__init__(config)
        self.callback = callback

    def send(self, data: str) -> Optional[str]:
        return self.callback(data)
