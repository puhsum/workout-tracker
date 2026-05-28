#!/usr/bin/env python3
import asyncio
import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Convert this workout log to an Obsidian markdown file.
Output ONLY the raw markdown — no explanation, no code fences.

Input:
{raw}

Output format:
---
created: YYYY-MM-DD HH:mm
date: YYYY-MM-DD
log-in: HH:mm
log-out:
duration:
tags:
  - project/workout
  - status/done
exercises:
  - name: <Title-cased name>
    sets: <formatted sets>
---

## Notes

<!-- No notes imported -->

Sets rules:
  squat 90(6), 90(6)   →  sets: 90(6), 90(6)
  dips 10, 10, 10      →  sets: (10), (10), (10)
  pullups 6, 6, 6      →  sets: (6), (6), (6)
  run 5mins            →  sets: duration: 5min
  bench 80kg 3x8       →  sets: 80(8), 80(8), 80(8)

Name rules: title-case, bb→Barbell, db→Dumbbell
Use logged_at for created, date, and log-in. Leave log-out and duration blank."""


async def convert_and_save(pending_path: Path, workouts_dir: Path) -> str:
    raw = pending_path.read_text(encoding="utf-8")
    date_str = pending_path.stem
    prompt = PROMPT_TEMPLATE.format(raw=raw)

    result = await asyncio.to_thread(
        subprocess.run,
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude exited {result.returncode}: {result.stderr.strip()}")

    md_content = result.stdout.strip()

    # Strip code fences if Claude adds them
    md_content = re.sub(r"^```[^\n]*\n", "", md_content)
    md_content = re.sub(r"\n```\s*$", "", md_content).strip()

    workouts_dir.mkdir(parents=True, exist_ok=True)
    out_path = workouts_dir / f"{date_str}.md"
    out_path.write_text(md_content + "\n", encoding="utf-8")
    pending_path.unlink(missing_ok=True)

    logger.info(f"Saved {out_path}")
    _git_push(workouts_dir.parent, out_path, date_str)

    return _summarize(md_content)


def _summarize(md: str) -> str:
    names = re.findall(r"^\s*-\s*name:\s*(.+)$", md, re.MULTILINE)
    if not names:
        return "Saved."
    lines = "\n".join(f"  • {n.strip()}" for n in names)
    return f"Logged:\n{lines}"


def _git_push(repo_root: Path, file_path: Path, date_str: str) -> None:
    try:
        rel = file_path.relative_to(repo_root)
        subprocess.run(["git", "-C", str(repo_root), "add", str(rel)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo_root), "commit", "-m", f"workout: {date_str}"],
            check=True, capture_output=True,
        )
        subprocess.run(["git", "-C", str(repo_root), "push"], check=True, capture_output=True)
        logger.info(f"Pushed workout: {date_str}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git push failed: {e.stderr.decode() if e.stderr else e}")
