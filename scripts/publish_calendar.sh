#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

TARGET="data/calendar.json"
VALIDATOR="scripts/validate_calendar.py"
BRANCH="${CALENDAR_BRANCH:-main}"
REMOTE="${CALENDAR_REMOTE:-origin}"

if [[ ! -f "$TARGET" ]]; then
  echo "ERROR: $TARGET is missing; refusing to publish." >&2
  exit 1
fi

python3 "$VALIDATOR" "$TARGET" --baseline-git HEAD

if git diff --quiet -- "$TARGET"; then
  echo "NO_CHANGES"
  exit 0
fi

# Only calendar.json belongs in the automated data commit.
git add -- "$TARGET"
git diff --cached --quiet && {
  echo "NO_CHANGES"
  exit 0
}

commit_date="$(TZ=Asia/Taipei date +%F)"
git commit -m "chore(calendar): sync student announcements ${commit_date}"

# Retry once if another writer advanced main between fetch and push.
for attempt in 1 2; do
  git fetch "$REMOTE" "$BRANCH"

  if ! git rebase "${REMOTE}/${BRANCH}"; then
    git rebase --abort || true
    echo "ERROR: rebase conflict while reconciling ${REMOTE}/${BRANCH}; refusing to push." >&2
    exit 1
  fi

  python3 "$VALIDATOR" "$TARGET" --baseline-git "${REMOTE}/${BRANCH}"

  if git push "$REMOTE" "HEAD:${BRANCH}"; then
    echo "PUSHED_COMMIT=$(git rev-parse HEAD)"
    exit 0
  fi

  if [[ "$attempt" -eq 1 ]]; then
    echo "Push raced with another update; fetching and retrying once." >&2
  fi
done

echo "ERROR: push failed after one retry; repository was not force-pushed." >&2
exit 1
