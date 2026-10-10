#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_CATEGORIES = {
    "獎助學金": "scholarship",
    "實習": "internship",
    "選課": "course",
    "考試": "exam",
    "講座": "talk",
    "競賽": "competition",
    "系上活動": "event",
}

REQUIRED_KEYS = [
    "id",
    "title",
    "category",
    "startDate",
    "endDate",
    "url",
    "audience",
    "description",
]

ID_RE = re.compile(
    r"^(scholarship|internship|course|exam|talk|competition|event)-(\d{4})-(\d{3})$"
)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json_text(text: str, source: str) -> list[dict[str, str]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        fail(f"{source} is not valid JSON: {exc}")

    if not isinstance(data, list):
        fail(f"{source} must contain a top-level JSON array.")
    if not data:
        fail(f"{source} must not be an empty array.")
    return data


def load_file(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        fail(f"{path} does not exist.")
    return load_json_text(path.read_text(encoding="utf-8"), str(path))


def load_git_file(ref: str, path: str) -> list[dict[str, str]]:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        fail(f"Unable to read baseline {ref}:{path}: {proc.stderr.strip()}")
    return load_json_text(proc.stdout, f"{ref}:{path}")


def parse_date(value: str, field: str, event_id: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        fail(f"{event_id}: {field} must be a real YYYY-MM-DD date, got {value!r}.")
    if parsed.isoformat() != value:
        fail(f"{event_id}: {field} must use canonical YYYY-MM-DD format.")
    return parsed


def validate_url(value: str, event_id: str) -> None:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"}:
        fail(f"{event_id}: url must use http or https.")
    if not (host == "uch.edu.tw" or host.endswith(".uch.edu.tw")):
        fail(f"{event_id}: url must point to an official uch.edu.tw host, got {host!r}.")


def validate_event(event: object, index: int) -> tuple[str, tuple[str, str, str]]:
    if not isinstance(event, dict):
        fail(f"Entry #{index + 1} must be an object.")

    keys = list(event.keys())
    if set(keys) != set(REQUIRED_KEYS):
        missing = sorted(set(REQUIRED_KEYS) - set(keys))
        extra = sorted(set(keys) - set(REQUIRED_KEYS))
        fail(f"Entry #{index + 1}: wrong fields; missing={missing}, extra={extra}.")

    for key in REQUIRED_KEYS:
        if not isinstance(event[key], str):
            fail(f"Entry #{index + 1}: field {key!r} must be a string.")

    event_id = event["id"]
    match = ID_RE.fullmatch(event_id)
    if not match:
        fail(f"{event_id or f'Entry #{index + 1}'}: invalid id format.")

    category = event["category"]
    if category not in ALLOWED_CATEGORIES:
        fail(f"{event_id}: invalid category {category!r}.")
    if match.group(1) != ALLOWED_CATEGORIES[category]:
        fail(f"{event_id}: id prefix does not match category {category!r}.")

    if not event["title"].strip():
        fail(f"{event_id}: title must not be blank.")

    start = parse_date(event["startDate"], "startDate", event_id)
    end = parse_date(event["endDate"], "endDate", event_id)
    if end < start:
        fail(f"{event_id}: endDate is earlier than startDate.")

    if int(match.group(2)) != start.year:
        fail(
            f"{event_id}: id year {match.group(2)} must match startDate year {start.year}."
        )

    validate_url(event["url"], event_id)

    signature = (
        category,
        re.sub(r"\s+", " ", event["title"].strip()).casefold(),
        event["startDate"],
    )
    return event_id, signature


def validate_new_id_sequence(
    baseline: list[dict[str, str]], candidate: list[dict[str, str]]
) -> None:
    baseline_ids = {item["id"] for item in baseline if isinstance(item, dict) and "id" in item}
    max_serial: dict[tuple[str, str], int] = {}

    for item in baseline:
        if not isinstance(item, dict):
            continue
        match = ID_RE.fullmatch(str(item.get("id", "")))
        if not match:
            continue
        key = (match.group(1), match.group(2))
        max_serial[key] = max(max_serial.get(key, 0), int(match.group(3)))

    new_by_group: dict[tuple[str, str], list[int]] = {}
    for item in candidate:
        event_id = item["id"]
        if event_id in baseline_ids:
            continue
        match = ID_RE.fullmatch(event_id)
        assert match is not None
        key = (match.group(1), match.group(2))
        serial = int(match.group(3))
        if serial <= max_serial.get(key, 0):
            fail(
                f"{event_id}: new id reuses or precedes the baseline maximum "
                f"{max_serial.get(key, 0):03d} for {key[0]}-{key[1]}."
            )
        new_by_group.setdefault(key, []).append(serial)

    for key, serials in new_by_group.items():
        if len(serials) != len(set(serials)):
            fail(f"Duplicate new serials detected for {key[0]}-{key[1]}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data/calendar.json")
    parser.add_argument(
        "--baseline-git",
        metavar="REF",
        help="Compare against REF:path and reject missing historical IDs by default.",
    )
    args = parser.parse_args()

    path = Path(args.path)
    candidate = load_file(path)

    ids: set[str] = set()
    signatures: set[tuple[str, str, str]] = set()

    for index, event in enumerate(candidate):
        event_id, signature = validate_event(event, index)
        if event_id in ids:
            fail(f"Duplicate id: {event_id}")
        ids.add(event_id)

        if signature in signatures:
            fail(
                f"Possible duplicate event: category/title/startDate collide at {event_id}."
            )
        signatures.add(signature)

    if args.baseline_git:
        baseline = load_git_file(args.baseline_git, args.path)
        baseline_ids = {
            item.get("id")
            for item in baseline
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        missing = sorted(event_id for event_id in baseline_ids if event_id not in ids)
        if missing and os.environ.get("CALENDAR_ALLOW_REMOVALS") != "1":
            fail(
                "Historical IDs are missing from the candidate: "
                + ", ".join(missing)
                + ". Set CALENDAR_ALLOW_REMOVALS=1 only for verified official "
                "withdrawals or duplicate cleanup."
            )
        validate_new_id_sequence(baseline, candidate)

    print(f"OK: validated {len(candidate)} calendar events.")


if __name__ == "__main__":
    main()
