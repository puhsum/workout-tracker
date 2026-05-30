#!/usr/bin/env python3
"""
Clean up exercise names in all workout-converted markdown files.
Run from the repo root: python dashboard/clean_exercises.py
"""

import re
from pathlib import Path

VAULT_DIR = Path(__file__).parent.parent / "workout-converted"

# ── Junk detection ────────────────────────────────────────────────────────────

_JUNK = re.compile(
    r'^\s*$'                  # empty
    r'|^\['                   # markdown / broken link
    r'|^https?://'            # raw URL
    r'|^#'                    # note / heading leak
    r'|^-\s*\['              # Notion checkbox leak
    r'|^Could Only'
    r'|^Yukari$'
    r'|^Gabe$'
    r'|^Up:?$'               # section header leak
    r'|^Press:?$'            # too ambiguous alone
    , re.IGNORECASE
)

# ── Cleaning transforms (applied in order) ────────────────────────────────────

# 1. Notion checkbox prefix: "- [X] Run" → "Run"
_CHECKBOX = re.compile(r'^-\s*\[[xX\s\-]\]\s*')

# 2. Duration prefix: "5Mins Run" → "Run", "3Min Cardio" → "Cardio"
_DURATION_PREFIX = re.compile(
    r'^\d+\.?\d*\s*(?:min|mins|minute|minutes|sec|secs|second|seconds|hr|hrs)\s+',
    re.IGNORECASE,
)

# 3. Trailing set data after colon: "Squat: Bar X5," → "Squat"
_TRAILING_SETS = re.compile(
    r'\s*:\s*(Bar|bar|\d|x\d|barx).*$',
    re.IGNORECASE,
)

# 4. Trailing noise: colons, dashes, spaces
_TRAILING_NOISE = re.compile(r'[\s:\-]+$')

# 5. Emoji
_EMOJI = re.compile(
    r'[\U0001F000-\U0001FFFF'
    r'\U00002600-\U000027BF'
    r'\U0000FE00-\U0000FE0F'
    r'\U00003000-\U0000303F]+',
    re.UNICODE,
)

# 6. Misspellings and normalizations  (pattern, replacement)
_FIXES = [
    # Misspellings
    (re.compile(r'\bSholder\b', re.I),              'Shoulder'),
    (re.compile(r'\bAbbs\b', re.I),                 'Abs'),
    (re.compile(r'\bAbb\b', re.I),                  'Abs'),
    (re.compile(r'\bFacepull\b', re.I),             'Face Pull'),
    (re.compile(r'\bGoodmorning\b', re.I),          'Good Morning'),
    (re.compile(r'\bRunning Machine\b', re.I),      'Treadmill'),
    (re.compile(r'\bFlys\b', re.I),                 'Flyes'),
    # Plurals → singular
    (re.compile(r'\bSquats\b', re.I),               'Squat'),
    (re.compile(r'\bPull-Ups\b', re.I),             'Pull-Up'),
    # Pulldown variants → canonical form
    (re.compile(r'\bCable Pull Downs\b', re.I),     'Cable Pulldown'),
    (re.compile(r'\bCable Pulldowns\b', re.I),      'Cable Pulldown'),
    (re.compile(r'\bCable Pull Down\b', re.I),      'Cable Pulldown'),
    (re.compile(r'\bLats Pull-Downs\b', re.I),      'Lat Pulldown'),
    (re.compile(r'\bLats Pull Down\b', re.I),       'Lat Pulldown'),
    (re.compile(r'\bLat Pull-Downs\b', re.I),       'Lat Pulldown'),
    (re.compile(r'\bMachine Pull\s*Down\b', re.I),  'Lat Pulldown'),
    (re.compile(r'\bPull Down Machine\b', re.I),    'Lat Pulldown'),
    (re.compile(r'\bMachine Pulldowns\b', re.I),    'Lat Pulldown'),
    (re.compile(r'\bWeighted Pull Downs\b', re.I),  'Weighted Pulldown'),
    (re.compile(r'\bLats Pullover\b', re.I),        'Lat Pullover'),
    (re.compile(r'\bLats Pull Over\b', re.I),       'Lat Pullover'),
    (re.compile(r'\bPull Downs\b', re.I),           'Lat Pulldown'),
    (re.compile(r'\bPulldowns\b', re.I),            'Lat Pulldown'),
    # Machine Row variants
    (re.compile(r'\bSeats Machine Pulls\b', re.I),  'Seated Row'),
    (re.compile(r'\bMachine Dumbbell Rows\b', re.I),'Seated Row'),
    (re.compile(r'\bMachine Rows\b', re.I),         'Seated Row'),
    (re.compile(r'\bMachine Row\b', re.I),          'Seated Row'),
    # Shoulder raise
    (re.compile(r'\bSholder Raise\b', re.I),        'Shoulder Raise'),
    (re.compile(r'\bSholder Press\b', re.I),        'Shoulder Press'),
    # Good Morning
    (re.compile(r'\bGood-Morning\b', re.I),         'Good Morning'),
]


def clean_name(raw: str):
    """Return a cleaned exercise name, or None to delete the entry."""
    name = raw.strip().strip('"').strip("'")
    if not name or _JUNK.match(name):
        return None

    name = _CHECKBOX.sub('', name).strip()
    name = _DURATION_PREFIX.sub('', name).strip()
    name = _TRAILING_SETS.sub('', name).strip()
    name = _TRAILING_NOISE.sub('', name).strip()
    name = _EMOJI.sub('', name).strip()
    name = _TRAILING_NOISE.sub('', name).strip()

    for pattern, replacement in _FIXES:
        name = pattern.sub(replacement, name)

    name = name.strip()
    if not name or _JUNK.match(name) or len(name) < 2:
        return None

    return name[0].upper() + name[1:]


# ── File processor ────────────────────────────────────────────────────────────

_NAME_LINE  = re.compile(r'^(\s+- name:\s*)(.*?)$')
_SETS_LINE  = re.compile(r'^\s+sets:\s*')
_FRONTMATTER = re.compile(r'^(---\n.*?\n---)(.*)', re.DOTALL)


def process_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        return False

    fm_match = _FRONTMATTER.match(text)
    if not fm_match:
        return False

    frontmatter, rest = fm_match.group(1), fm_match.group(2)
    lines = frontmatter.split('\n')
    new_lines = []
    changed = False
    i = 0

    while i < len(lines):
        line = lines[i]
        m = _NAME_LINE.match(line)
        if m:
            prefix, raw_name = m.group(1), m.group(2)
            cleaned = clean_name(raw_name)

            if cleaned is None:
                # Drop this name line + the following sets line
                changed = True
                i += 1
                if i < len(lines) and _SETS_LINE.match(lines[i]):
                    i += 1
                continue

            new_line = f'{prefix}"{cleaned}"'
            if new_line != line:
                changed = True
            new_lines.append(new_line)
        else:
            new_lines.append(line)
        i += 1

    if not changed:
        return False

    path.write_text('\n'.join(new_lines) + rest, encoding='utf-8')
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not VAULT_DIR.exists():
        print(f"Vault not found: {VAULT_DIR}")
        return

    files = sorted(VAULT_DIR.glob("*.md"))
    modified, skipped_names = 0, []

    for path in files:
        if process_file(path):
            modified += 1
            print(f"  cleaned: {path.name}")

    print(f"\nDone. Modified {modified} of {len(files)} files.")


if __name__ == "__main__":
    main()
