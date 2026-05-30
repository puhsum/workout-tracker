import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


def create_session() -> dict:
    sid = str(uuid.uuid4())
    session = {
        "id": sid,
        "start_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "exercises": [],
    }
    _write(session)
    return session


def get_session(sid: str) -> dict | None:
    p = SESSIONS_DIR / f"{sid}.json"
    return json.loads(p.read_text()) if p.exists() else None


def add_exercise(sid: str, name: str, sets: list) -> dict | None:
    s = get_session(sid)
    if s is None:
        return None
    s["exercises"].append({"name": name, "sets": sets})
    _write(s)
    return s


def remove_exercise(sid: str, index: int) -> dict | None:
    s = get_session(sid)
    if s is None:
        return None
    if 0 <= index < len(s["exercises"]):
        s["exercises"].pop(index)
        _write(s)
    return s


def finish_session(sid: str) -> dict | None:
    s = get_session(sid)
    if s is None:
        return None
    s["end_time"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write(s)
    return s


def delete_session(sid: str):
    p = SESSIONS_DIR / f"{sid}.json"
    if p.exists():
        p.unlink()


def _write(s: dict):
    p = SESSIONS_DIR / f"{s['id']}.json"
    p.write_text(json.dumps(s, indent=2))
