from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

_lock = Lock()
_STATE_PATH = Path(os.getenv("SYNC_STATE_PATH", "/tmp/veriqrahq-sync-state.json"))
_DEFAULT_STATE: dict[str, Any] = {
    "running": False,
    "task": "idle",
    "message": "Sin sincronizaciones en curso.",
    "started_at": None,
    "finished_at": None,
    "updated_at": None,
    "processed": 0,
    "imported": 0,
    "updated": 0,
    "error": None,
}
_state: dict[str, Any] = dict(_DEFAULT_STATE)


def _load_state() -> dict[str, Any]:
    if not _STATE_PATH.exists():
        return dict(_state)
    try:
        data = json.loads(_STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return dict(_state)
    state = {**_DEFAULT_STATE, **data}
    if _is_stale(state):
        state.update(
            running=False,
            message="Sincronizacion anterior detenida o finalizada sin cierre registrado.",
            finished_at=datetime.utcnow().isoformat(),
            error="Estado de sincronizacion obsoleto",
        )
    return state


def _is_stale(state: dict[str, Any]) -> bool:
    if not state.get("running"):
        return False
    updated_at = state.get("updated_at") or state.get("started_at")
    if not updated_at:
        return True
    try:
        updated = datetime.fromisoformat(str(updated_at))
    except ValueError:
        return True
    return datetime.utcnow() - updated > timedelta(minutes=15)


def _touch() -> None:
    _state["updated_at"] = datetime.utcnow().isoformat()


def _save_state() -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = _STATE_PATH.with_suffix(f"{_STATE_PATH.suffix}.tmp")
    temp_path.write_text(json.dumps(_state, ensure_ascii=False))
    os.replace(temp_path, _STATE_PATH)
    try:
        os.chmod(_STATE_PATH, 0o666)
    except OSError:
        pass


def start(task: str, message: str) -> None:
    with _lock:
        _state.update(_load_state())
        _state.update(
            running=True,
            task=task,
            message=message,
            started_at=datetime.utcnow().isoformat(),
            finished_at=None,
            updated_at=datetime.utcnow().isoformat(),
            processed=0,
            imported=0,
            updated=0,
            error=None,
        )
        _save_state()


def progress(message: str, *, processed: int | None = None, imported: int | None = None, updated: int | None = None) -> None:
    with _lock:
        _state.update(_load_state())
        _state["message"] = message
        _touch()
        if processed is not None:
            _state["processed"] = processed
        if imported is not None:
            _state["imported"] = imported
        if updated is not None:
            _state["updated"] = updated
        _save_state()


def finish(message: str, *, imported: int = 0, updated: int = 0, processed: int | None = None) -> None:
    with _lock:
        _state.update(_load_state())
        _state.update(
            running=False,
            message=message,
            imported=imported,
            updated=updated,
            finished_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            error=None,
        )
        if processed is not None:
            _state["processed"] = processed
        _save_state()


def fail(message: str) -> None:
    with _lock:
        _state.update(_load_state())
        _state.update(
            running=False,
            message=message,
            error=message,
            finished_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        _save_state()


def get_state() -> dict[str, Any]:
    with _lock:
        _state.update(_load_state())
        return dict(_state)
