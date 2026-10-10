# Codex Cloud scheduled task

Run the daily UCH student-announcement calendar sync for this repository.

Follow `AGENTS.md` exactly. Use public web access to inspect official `uch.edu.tw` pages and use the repository's scripts for validation and publishing.

Required outcome:

1. Read `data/calendar.example.json` and the complete current `data/calendar.json`.
2. Search official UCH notices for the allowed seven categories, prioritizing the last 30 days and still-open/future notices.
3. Merge only verified official information into the full existing array while preserving IDs and historical records.
4. Run `python3 scripts/validate_calendar.py data/calendar.json --baseline-git HEAD`.
5. If there is no valid change, leave the file untouched and report `NO_CHANGES`.
6. If there is a valid change, run `bash scripts/publish_calendar.sh`.
7. Treat the task as successful only when the publish script returns `PUSHED_COMMIT=<sha>`.
8. Never force-push, never replace existing data with `[]`, and never claim a push succeeded without the returned commit SHA.
9. On any failure, report the failing step and error and leave the existing remote data intact.
