import json
import time
import uuid
import functools
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

current_session_id: ContextVar[str] = ContextVar("current_session_id", default="no_session")

LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "sessions"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def new_session() -> str:
    sid = str(uuid.uuid4())
    current_session_id.set(sid)
    _log({
        "type": "session_start",
        "session_id": sid,
        "timestamp": _now(),
    })
    return sid


def end_session(status: str = "success", note: str | None = None) -> None:
    _log({
        "type": "session_end",
        "session_id": current_session_id.get(),
        "status": status,
        "note": note,
        "timestamp": _now(),
    })


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(record: dict) -> None:
    sid = record.get("session_id") or "no_session"
    log_file = LOG_DIR / f"{sid}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_tool(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        sid = current_session_id.get()
        start = time.time()
        record = {
            "type": "tool_call",
            "tool_name": func.__name__,
            "session_id": sid,
            "args": kwargs if kwargs else list(args),
            "started_at": _now(),
        }
        try:
            result = func(*args, **kwargs)
            record.update({
                "ended_at": _now(),
                "duration_ms": int((time.time() - start) * 1000),
                "success": True,
                "result_preview": str(result)[:300],
            })
            _log(record)
            return result
        except Exception as e:
            record.update({
                "ended_at": _now(),
                "duration_ms": int((time.time() - start) * 1000),
                "success": False,
                "error": f"{type(e).__name__}: {e}",
            })
            _log(record)
            raise
    return wrapper
