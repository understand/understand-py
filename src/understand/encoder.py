import inspect
from pathlib import Path
import traceback
from types import TracebackType
from typing import Any, Dict, Iterable, List, Optional

from .config import UnderstandConfig


class ExceptionEncoder:
    def __init__(self, config: Optional[UnderstandConfig] = None) -> None:
        self.config = config or UnderstandConfig()

    def exception_to_dict(self, exception: BaseException) -> Dict[str, Any]:
        if not isinstance(exception, BaseException):
            raise TypeError("exception must be an instance of BaseException")

        frames = self._traceback_to_frames(exception.__traceback__)
        top = frames[-1] if frames else None
        file_name = self._relative_path(top.filename) if top else None
        line = top.lineno if top else None
        class_name = exception.__class__.__name__
        message = str(exception) if str(exception) else class_name

        return {
            "message": message,
            "class": class_name,
            "code": getattr(exception, "errno", None),
            "file": file_name,
            "line": line,
            "stack": self.stack_trace_to_list(frames),
        }

    def set_current_stack_trace(self, error_log: Dict[str, Any]) -> Dict[str, Any]:
        frames = [
            frame
            for frame in inspect.stack()[1 : self.config.stack_trace_limit + 1]
            if "/understand/" not in frame.filename.replace("\\", "/")
        ]
        stack = self.stack_trace_to_list(frames)
        if stack:
            error_log["class"] = None
            error_log["file"] = stack[0]["file"]
            error_log["line"] = stack[0]["line"]
        error_log["stack"] = stack
        return error_log

    def stack_trace_to_list(self, frames: Iterable[Any]) -> List[Dict[str, Any]]:
        stack = []
        for frame in list(frames)[-self.config.stack_trace_limit :]:
            filename = getattr(frame, "filename", None)
            lineno = getattr(frame, "lineno", None)
            function = getattr(frame, "name", None) or getattr(frame, "function", None)
            relative = self._relative_path(filename) if filename else None
            stack.append(
                {
                    "class": None,
                    "function": function,
                    "args": [],
                    "type": "function",
                    "file": relative,
                    "line": lineno,
                    "code": self.get_code(relative, lineno),
                }
            )
        return stack

    def get_code(self, relative_path: Optional[str], line: Optional[int], lines_around: int = 6) -> Optional[List[Dict[str, Any]]]:
        if not relative_path or not line:
            return None

        path = self.config.project_root / relative_path
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None

        start = max(1, line - lines_around)
        end = min(len(lines), line + lines_around)
        return [{"line": number, "code": lines[number - 1][:250].rstrip()} for number in range(start, end + 1)]

    def _traceback_to_frames(self, tb: Optional[TracebackType]) -> List[traceback.FrameSummary]:
        if tb is None:
            return []
        return traceback.extract_tb(tb)

    def _relative_path(self, filename: Optional[str]) -> Optional[str]:
        if filename is None:
            return None

        path = Path(filename)
        try:
            return str(path.resolve().relative_to(self.config.project_root.resolve()))
        except ValueError:
            return str(path)

