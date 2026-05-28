#!/usr/bin/env python3
import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path

import google.generativeai as genai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Convert a free-text workout log into an Obsidian markdown file.
Output ONLY the raw markdown — no explanation, no code fences, nothing else.

Input format:
  logged_at: YYYY-MM-DD HH:MM
  ---
  <exercise lines>

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

Sets formatting:
  squat 90(6), 90(6), 90(6)  →  sets: 90(6), 90(6), 90(6)
  dips 10, 10, 10             →  sets: (10), (10), (10)
  pullups 6, 6, 6             →  sets: (6), (6), (6)
  run 5mins                   →  sets: duration: 5min
  bench 80kg 3x8              →  sets: 80(8), 80(8), 80(8)
  squat 60(6), 90(6)x4        →  sets: 60(6), 90(6), 90(6), 90(6), 90(6)

Name rules:
  - Title-case every word
  - bb → Barbell, db → Dumbbell
  - Use logged_at for created, date, and log-in
  - Leave log-out and duration blank"""


async def convert_and_save(pending_path: Path, workouts_dir: Path) -> str:
    raw = pending_path.read_text(encoding="utf-8")
    date_str = pending_path.stem

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )

    response = await asyncio.to_thread(model.generate_content, raw)
    md_content = response.text.strip()

    # Strip code fences if Gemini wraps the output anyway
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
        logger.error(f"Git operation failed: {e.stderr.decode() if e.stderr else e}")
