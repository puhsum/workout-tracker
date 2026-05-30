from datetime import datetime
from pathlib import Path


def _yaml_str(value: str) -> str:
    """Return a safely quoted YAML string value."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _fmt_sets(sets: list) -> str:
    if not sets:
        return '""'
    if sets[0].get("type") == "duration":
        dur = sets[0].get("duration", "?")
        return f'"duration: {dur}"'
    parts = []
    for s in sets:
        weight = s.get("weight")
        reps = s.get("reps", "?")
        if weight:
            parts.append(f"{weight}({reps})")
        else:
            parts.append(f"({reps})")
    return f'"{", ".join(parts)}"'


def write_workout(session: dict, vault_dir: Path) -> str:
    vault_dir.mkdir(parents=True, exist_ok=True)

    start = datetime.fromisoformat(session["start_time"]).astimezone()
    end = datetime.fromisoformat(session["end_time"]).astimezone()
    duration = max(1, int((end - start).total_seconds() / 60))
    date_str = start.strftime("%Y-%m-%d")
    log_in = start.strftime("%H:%M")
    log_out = end.strftime("%H:%M")
    created = start.strftime("%Y-%m-%d %H:%M")

    exercises_yaml = ""
    for ex in session.get("exercises", []):
        name = _yaml_str(str(ex.get("name", "")).strip())
        sets_str = _fmt_sets(ex.get("sets", []))
        exercises_yaml += f"  - name: {name}\n    sets: {sets_str}\n"

    if not exercises_yaml:
        exercises_yaml = "  []\n"

    content = (
        f"---\n"
        f"created: {created}\n"
        f"date: {date_str}\n"
        f'log-in: "{log_in}"\n'
        f'log-out: "{log_out}"\n'
        f"duration: {duration}\n"
        f"tags:\n"
        f"  - project/workout\n"
        f"  - status/done\n"
        f"exercises:\n"
        f"{exercises_yaml}"
        f"---\n\n"
        f"## Notes\n\n"
    )

    base = f"{date_str} {log_in.replace(':', '-')}"
    candidate = vault_dir / f"{base}.md"
    suffix = 1
    while candidate.exists():
        candidate = vault_dir / f"{base} {suffix}.md"
        suffix += 1

    candidate.write_text(content, encoding="utf-8")
    return candidate.name
