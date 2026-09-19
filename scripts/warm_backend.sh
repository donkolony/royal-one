#!/usr/bin/env bash
# Wake a sleeping free-tier backend before a demo. Usage: scripts/warm_backend.sh https://<backend-host>
set -euo pipefail
BASE="${1:-http://localhost:8000}"
for i in 1 2 3 4 5 6; do
  if curl -fsS --max-time 60 "$BASE/health" >/dev/null; then
    echo "Backend is up: $BASE"
    exit 0
  fi
  echo "Attempt $i failed, retrying..."
  sleep 5
done
echo "Backend did not respond at $BASE" >&2
exit 1
