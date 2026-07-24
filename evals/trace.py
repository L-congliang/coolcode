"""JSONL trace recording for eval runs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any


MAX_FIELD_CHARS = 2000


def _truncate(value: Any, limit: int = MAX_FIELD_CHARS) -> Any:
    if isinstance(value, str):
        if len(value) <= limit:
            return value
        return value[:limit] + f"... [truncated {len(value) - limit} chars]"
    if isinstance(value, dict):
        return {str(k): _truncate(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate(item, limit) for item in value]
    return value


class TraceRecorder:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.events: list[dict[str, Any]] = []
        self._fh = self.path.open("w", encoding="utf-8")

    def close(self) -> None:
        self._fh.close()

    def record(self, event: str, **fields: Any) -> dict[str, Any]:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **_truncate(fields),
        }
        self.events.append(payload)
        self._fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        self._fh.flush()
        return payload

    @property
    def tool_calls(self) -> list[dict[str, Any]]:
        return [event for event in self.events if event.get("event") == "tool_call"]

    @property
    def tool_results(self) -> list[dict[str, Any]]:
        return [event for event in self.events if event.get("event") == "tool_result"]

    @property
    def tool_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in self.tool_calls:
            tool = str(event.get("tool", ""))
            counts[tool] = counts.get(tool, 0) + 1
        return counts


def duration_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)

