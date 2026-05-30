import re
import yaml
from pathlib import Path
from datetime import date, timedelta
from typing import Any, Dict, List, Optional


def parse_workouts(workouts_dir: Path) -> List[Dict[str, Any]]:
    if not workouts_dir.exists():
        return []
    workouts = []
    for md_file in sorted(workouts_dir.glob("*.md"), reverse=True):
        w = _parse_file(md_file)
        if w:
            workouts.append(w)
    return workouts


def _parse_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None

    try:
        fm = yaml.safe_load(_quote_sets_values(match.group(1)))
    except yaml.YAMLError:
        return None

    if not fm:
        return None

    exercises = []
    for ex in fm.get("exercises") or []:
        if not isinstance(ex, dict) or not ex.get("name"):
            continue
        sets_raw = str(ex.get("sets", ""))
        parsed = _parse_sets(sets_raw)
        exercises.append({
            "name": str(ex["name"]).strip(),
            "sets_raw": sets_raw,
            "sets": parsed,
            "max_weight": max((s["weight"] for s in parsed if s["weight"] > 0), default=0),
            "total_volume": sum(s["weight"] * s["reps"] for s in parsed),
        })

    date_val = fm.get("date")
    if hasattr(date_val, "strftime"):
        date_str = date_val.strftime("%Y-%m-%d")
    else:
        date_str = str(date_val or path.stem)[:10]

    return {
        "date": date_str,
        "log_in": str(fm.get("log-in") or ""),
        "duration": str(fm.get("duration") or ""),
        "exercises": exercises,
        "exercise_names": [e["name"] for e in exercises],
    }


def _quote_sets_values(yaml_str: str) -> str:
    """Quote 'sets:' values that contain a colon so PyYAML doesn't treat them as nested mappings."""
    def _quote(m: re.Match) -> str:
        val = m.group(2)
        if val.startswith('"') or val.startswith("'"):
            return m.group(0)
        val = val.replace('"', '\\"')
        return f'{m.group(1)}"{val}"'
    return re.sub(r'^(\s+sets:\s+)(.+)$', _quote, yaml_str, flags=re.MULTILINE)


def _parse_sets(sets_str: str) -> List[Dict]:
    if not sets_str or "duration" in sets_str.lower():
        return []
    sets = []
    for part in sets_str.split(","):
        m = re.match(r"^\s*(\d+\.?\d*)?\((\d+)\)\s*$", part)
        if m:
            sets.append({
                "weight": float(m.group(1)) if m.group(1) else 0.0,
                "reps": int(m.group(2)),
            })
    return sets


_DURATION_PREFIX = re.compile(
    r'^\d+\.?\d*\s*(?:min|mins|minute|minutes|sec|secs|second|seconds|hr|hrs|hour|hours)\s+',
    re.IGNORECASE,
)


def _normalize_exercise_name(name: str) -> str:
    """Strip leading duration tokens ('10min ', '3mins ', '30 minute ') from exercise names."""
    cleaned = _DURATION_PREFIX.sub('', name.strip())
    if not cleaned:
        return name.strip()
    return cleaned[0].upper() + cleaned[1:]


def get_exercise_names(workouts: List[Dict]) -> List[str]:
    """Return sorted unique exercise names, normalized so duration prefixes are removed."""
    seen: set[str] = set()
    names: list[str] = []
    for w in workouts:
        for raw in w.get("exercise_names", []):
            normalized = _normalize_exercise_name(raw)
            key = normalized.lower()
            if key not in seen:
                seen.add(key)
                names.append(normalized)
    return sorted(names)


def compute_stats(workouts: List[Dict]) -> Dict:
    if not workouts:
        return {"total": 0, "this_week": 0, "streak": 0, "last_workout": "—"}

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    dates_set: set = set()
    this_week = 0
    for w in workouts:
        try:
            d = date.fromisoformat(w["date"])
            dates_set.add(d)
            if d >= week_start:
                this_week += 1
        except (ValueError, TypeError):
            pass

    # Streak: consecutive days ending today or yesterday
    streak = 0
    check = today
    if check not in dates_set:
        check = today - timedelta(days=1)
    while check in dates_set:
        streak += 1
        check -= timedelta(days=1)

    return {
        "total": len(workouts),
        "this_week": this_week,
        "streak": streak,
        "last_workout": workouts[0]["date"] if workouts else "—",
    }
