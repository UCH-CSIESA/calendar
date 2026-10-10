# UCH student calendar sync

This repository is the source of truth for the student-announcement calendar.

## Scope

Maintain `data/calendar.json` from official Chien Hsin University of Science and Technology (`uch.edu.tw`) sources only.

Allowed categories:

- `獎助學金`
- `實習`
- `選課`
- `考試`
- `講座`
- `競賽`
- `系上活動`

Do not add unrelated notices.

## Required workflow for the scheduled sync

1. Start from a clean checkout of `main`.
2. Read `data/calendar.example.json`.
3. Read the complete current `data/calendar.json`. Never assume the previous dataset is empty.
4. Search official UCH pages, prioritizing:
   - notices published in the last 30 days;
   - notices whose application/activity deadline is still in the future;
   - CSIE, EECS, Academic Affairs, Student Affairs, and other official `uch.edu.tw` units.
5. Open the official notice itself before adding or changing an event. Do not use third-party pages as the factual source.
6. Merge findings into the existing full array. Preserve historical events and IDs.
7. Edit only `data/calendar.json` for the daily data sync.
8. Run:
   `python3 scripts/validate_calendar.py data/calendar.json --baseline-git HEAD`
9. If validation fails, stop. Do not publish partial or fallback data.
10. Publish with:
    `bash scripts/publish_calendar.sh`
11. Report either:
    - `NO_CHANGES`, or
    - the `PUSHED_COMMIT=<sha>` returned by the script.
    If a step fails, report the failing step and do not claim success.

## Event schema

Every event must contain exactly these string fields:

`id`, `title`, `category`, `startDate`, `endDate`, `url`, `audience`, `description`

Missing factual values must be `""`; never invent them.

### IDs

Existing IDs are permanent.

New IDs use:

`<prefix>-<YYYY>-<NNN>`

Prefixes:

- 獎助學金 → `scholarship`
- 實習 → `internship`
- 選課 → `course`
- 考試 → `exam`
- 講座 → `talk`
- 競賽 → `competition`
- 系上活動 → `event`

For each prefix/year, allocate a serial strictly above the current maximum. Never renumber old entries.

Treat two records as the same event by considering URL, title, dates, and notice contents together. An official correction may update an existing event without changing its ID.

### Dates

Use Taiwan-local `YYYY-MM-DD`.

- Prefer the explicit activity/application/course/exam start date.
- If no explicit start exists, use the official publication date.
- `endDate` is the explicit end/deadline.
- Single-day events use the same start/end date.
- If no explicit end exists, set `endDate = startDate`.
- Never infer a date that the notice does not state.

### URL

`url` must be a reachable official `uch.edu.tw` page for the event.

### Audience

Only copy an audience explicitly stated by the notice. Otherwise use `""`.

### Description

Summarize only useful facts explicitly present in the notice, such as venue, eligibility, registration method, and required documents. No advice or speculation.

## Safety invariants

- Never replace a non-empty `data/calendar.json` with `[]`.
- Never delete historical IDs just because an event expired.
- Never force-push.
- Never bypass validator failures.
- Never overwrite a concurrent update. The publish script rebases and retries a rejected push once.
- Deletions are blocked by default. Only for a verified official withdrawal or confirmed duplicate cleanup may you run validation/publish with `CALENDAR_ALLOW_REMOVALS=1`, and the task report must state why.
- If reading the baseline, browsing sources, validating, rebasing, or pushing fails, leave the repository data unchanged.
