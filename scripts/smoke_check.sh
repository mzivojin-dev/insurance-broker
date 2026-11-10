#!/usr/bin/env bash
# Every agent answers /health. Usage: smoke_check.sh http://localhost:8080 (local stack) or https://prod.example.com
set -euo pipefail
base="${1:?base URL required}"
for agent in client_service submission_intake book_analyst; do
  curl -fsS --retry 5 --retry-delay 5 "$base/$agent/health" > /dev/null
  echo "ok  $agent"
done
