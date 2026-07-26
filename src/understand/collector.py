from typing import Any, Dict, List, Optional


class DataCollector:
    def __init__(self, limit: int = 50) -> None:
        self._data: Dict[str, Any] = {}
        self.limit = limit

    def set_limit(self, limit: int) -> None:
        self.limit = limit

    def reset(self) -> None:
        self._data = {}

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def set_in_array(self, key: str, value: Any) -> None:
        values: List[Any] = list(self._data.get(key, []))
        if len(values) > self.limit - 1:
            values.pop(0)
        values.append(value)
        self._data[key] = values

    def get_by_key(self, key: str) -> Optional[Any]:
        return self._data.get(key)

