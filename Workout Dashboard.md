# Workout Dashboard

> [!tip] Setup
> 
> - Install the **Dataview** plugin and enable **DataviewJS** in its settings
> - Change `"Workouts"` in each query to match your exact folder name if different

---

## This month

```dataviewjs
const today = dv.date("today");
const pages = dv.pages('"workout-converted"')
  .where(p => {
    if (!p.date) return false;
    const d = dv.luxon.DateTime.fromMillis(Number(p.date));
    if (!d.isValid) return false;
    return d.month === today.month && d.year === today.year;
  })
  .sort(p => p.date, "desc");

const count = pages.length;
const durations = pages.where(p => p.duration).map(p => Number(p.duration)).array();
const totalMins = durations.reduce((a, b) => a + b, 0);
const avgMins = durations.length ? Math.round(totalMins / durations.length) : "—";

dv.paragraph(`**Sessions:** ${count}  ·  **Total time:** ${totalMins} min  ·  **Avg duration:** ${avgMins} min`);
```



---

## Recent sessions

```dataview
TABLE
  date AS "Date",
  log-in AS "Log in",
  log-out AS "Log out",
  duration + " min" AS "Duration",
  tags AS "Status"
FROM "workout-converted"
SORT date DESC
LIMIT 10
```

---

## All sessions — full list

```dataview
TABLE
  date AS "Date",
  duration + " min" AS "Duration"
FROM "workout-converted"
WHERE contains(tags, "project/workout")
SORT date DESC
```

---

## Sessions per month

```dataviewjs
const pages = dv.pages('"workout-converted"').where(p => p.date);

const counts = {};
for (let p of pages) {
  const d = dv.date(p.date);
  if (!d) continue;
  const key = `${d.year}-${String(d.month).padStart(2, "0")}`;
  counts[key] = (counts[key] || 0) + 1;
}

const sorted = Object.entries(counts).sort((a, b) => b[0].localeCompare(a[0]));

dv.table(
  ["Month", "Sessions", ""],
  sorted.map(([month, n]) => [
    month,
    n,
    "█".repeat(n)
  ])
);
```

---

## Done vs not started

```dataview
TABLE
  date AS "Date",
  file.link AS "Note"
FROM "workout-converted"
WHERE !contains(tags, "status/done")
SORT date DESC
```