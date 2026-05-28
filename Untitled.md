asdasd

```dataviewjs
dv.pages('"workout-converted"')
  .slice(0, 5)
  .forEach(p => dv.paragraph(
    p.file.name + " → date: `" + p.date + "` → parsed: `" + dv.date(p.date) + "`"
  ));
```

