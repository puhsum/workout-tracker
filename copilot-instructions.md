Context
I have a folder of Markdown files exported from Notion at C:\Users\gabrsc\OneDrive - ASSA ABLOY Group\Desktop\gym-logs\Notion\workout-tracker. Each file is a workout session log.
I want you to rewrite each file to match the Obsidian template below.

Source format (Notion export)
The frontmatter looks like this:
yaml---
📚 Projects:
  - e39ba6fd-5733-4241-b252-d6006550c5cd
IDEAS.db: []
Global_Tags.db: []
Last edited time: 2024-10-17T09:55:00
Date: 2024-10-17
Done: true
Created time: 2024-10-17T09:23:00
---
The body is free-text exercises, one per line, like:
3mins run
Hyperextension 3x10
Bb shoulder press 30kg 3x10
db Chest press  3x10 15kg, 17.5kg,
Cable pull downs 50kg 1x10, 65 2x10
Cable rows 55 1x10, 45 1x10
Face pull 2x10

Target format (Obsidian template)
yaml---
created: <Created time value, formatted as YYYY-MM-DD HH:mm>
date: <Date value, formatted as YYYY-MM-DD>
log-in: <leave blank — cannot be inferred>
log-out: <leave blank — cannot be inferred>
duration: <leave blank — cannot be inferred>
tags:
  - project/workout
  - status/done   # use status/done if Done: true, otherwise status/not-started
exercises:
  - name: <exercise name, cleaned up — see rules below>
    sets: <sets formatted as weight(reps), weight(reps) — see rules below>
---

## Notes

<!-- No notes imported from Notion -->

Conversion rules
Frontmatter

created → from Created time, reformat to YYYY-MM-DD HH:mm (drop seconds)
date → from Date as-is
log-in → from Created time, formatted as HH:mm
log-out → from Last edited time, formatted as HH:mm
duration → calculate the difference between log-out and log-in in minutes, output as a plain integer (e.g. 92)
tags → always include project/workout; add status/done if Done: true, else status/not-started
Strip all Notion-specific keys: 📚 Projects, IDEAS.db, Global_Tags.db, Last edited time

Exercise name cleanup

Expand common abbreviations: Bb → Barbell, Db → Dumbbell
Title-case the exercise name: bb shoulder press → Barbell shoulder press
Strip trailing/leading whitespace

Sets formatting
Convert free-text sets into the standard format: weight(reps), weight(reps), ...
Source formatOutput format3x10 with a weight prefix (e.g. 30kg 3x10)30(10), 30(10), 30(10)Multiple weights for different sets (e.g. 15kg, 17.5kg with 3x10)15(10), 17.5(10), 17.5(10) — apply the extra weight to the remaining sets1x10, 2x10 format with weights (e.g. 50kg 1x10, 65 2x10)50(10), 65(10), 65(10)Cardio/time-based (e.g. 3mins run, 5min)use duration: 3min instead of weight/repsWeight unit kg — keep it. If no unit, assume kg
If the format is ambiguous or cannot be parsed confidently, keep the original text as-is inside the sets: value and add a # TODO: check format comment after it.
Body / notes

Remove the original free-text exercise lines from the body (they move into the frontmatter exercises list)
If there is any non-exercise text in the body (e.g. personal notes, mood, injury mentions), keep it under ## Notes
If the body had no non-exercise text, leave the ## Notes section with the placeholder comment


Example conversion
Input file (2024-10-17.md)
---
📚 Projects:
  - e39ba6fd-5733-4241-b252-d6006550c5cd
IDEAS.db: []
Global_Tags.db: []
Last edited time: 2024-10-17T09:55:00
Date: 2024-10-17
Done: true
Created time: 2024-10-17T09:23:00
---
3mins run
Hyperextension 3x10
Bb shoulder press 30kg 3x10
db Chest press  3x10 15kg, 17.5kg,
Cable pull downs 50kg 1x10, 65 2x10
Cable rows 55 1x10, 45 1x10
Face pull 2x10
Expected output
yaml---
created: 2024-10-17 09:23
date: 2024-10-17
log-in: 09:23
log-out: 09:55
duration: 32
tags:
  - project/workout
  - status/done
exercises:
  - name: Run
    sets: duration: 3min
  - name: Hyperextension
    sets: (10), (10), (10)
  - name: Barbell shoulder press
    sets: 30(10), 30(10), 30(10)
  - name: Dumbbell chest press
    sets: 15(10), 17.5(10), 17.5(10)
  - name: Cable pull downs
    sets: 50(10), 65(10), 65(10)
  - name: Cable rows
    sets: 55(10), 45(10)
  - name: Face pull
    sets: (10), (10) # TODO: check format — no weight found
---

## Notes

<!-- No notes imported from Notion -->