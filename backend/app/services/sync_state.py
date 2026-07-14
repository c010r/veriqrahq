from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any

_lock = Lock()
_state: dict[str, Any] = {
    "running": False,
    "task": "idle",
    "message": "Sin sincronizaciones en curso.",
    "started_at": None,
    "finished_at": None,
    "processed": 0,
    "imported": 0,
    "updated": 0,
    "error": None,
}


def start(task: str, message: str) -> None:
    with _lock:
        _state.update(
            running=True,
            task=task,
            message=message,
            started_at=datetime.utcnow().isoformat(),
            finished_at=None,
            processed=0,
            imported=0,
            updated=0,
            error=None,
        )


def progress(message: str, *, processed: int | None = None, imported: int | None = None, updated: int | None = None) -> None:
    with _lock:
        _state["message"] = message
        if processed is not None:
            _state["processed"] = processed
        if imported is not None:
            _state["imported"] = imported
        if updated is not None:
            _state["updated"] = updated


def finish(message: str, *, imported: int = 0, updated: int = 0, processed: int | None = None) -> None:
    with _lock:
        _state.update(
            running=False,
            message=message,
            imported=imported,
            updated=updated,
            finished_at=datetime.utcnow().isoformat(),
            error=None,
        )
        if processed is not None:
            _state["processed"] = processed


def fail(message: str) -> None:
    with _lock:
        _state.update(
            running=False,
            message=message,
            error=message,
            finished_at=datetime.utcnow().isoformat(),
        )


def get_state() -> dict[str, Any]:
    with _lock:
        return dict(_state)
