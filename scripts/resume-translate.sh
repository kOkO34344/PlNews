#!/usr/bin/env bash
# Keep retrying a translation until it completes.
#
# The Claude Code backend runs on a subscription with a daily ceiling, so a long
# translation can stop half-way. `plnews translate` is resumable and exits 2 when work
# remains, so this just re-runs it on a slow loop until it exits 0.
#
#   scripts/resume-translate.sh bg            # foreground
#   nohup scripts/resume-translate.sh bg &    # detached, survives the terminal
#
# Stop it with: pkill -f resume-translate.sh
set -uo pipefail

LANG_CODE="${1:-bg}"
INTERVAL="${INTERVAL:-1800}"     # 30 minutes between attempts
MAX_ATTEMPTS="${MAX_ATTEMPTS:-48}"   # ~24 hours, then give up rather than loop forever
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
LOG="$ROOT/data/translate-$LANG_CODE.log"

[ -x "$PY" ] || PY="python3"
mkdir -p "$(dirname "$LOG")"

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  echo "=== attempt $attempt/$MAX_ATTEMPTS · $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
  ( cd "$ROOT" && "$PY" -m app.cli translate "$LANG_CODE" ) >> "$LOG" 2>&1
  status=$?
  if [ "$status" -eq 0 ]; then
    echo "=== complete after $attempt attempt(s)" >> "$LOG"
    exit 0
  fi
  echo "=== incomplete (exit $status); retrying in ${INTERVAL}s" >> "$LOG"
  sleep "$INTERVAL"
done

echo "=== gave up after $MAX_ATTEMPTS attempts" >> "$LOG"
exit 1
