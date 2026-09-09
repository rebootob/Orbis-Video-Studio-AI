#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
: "${WP020_LIVE_EXECUTION_ID:?missing WP020_LIVE_EXECUTION_ID}"
: "${GITHUB_SHA:?missing GITHUB_SHA}"
: "${ISSUE_NUMBER:?missing ISSUE_NUMBER}"

AUTH_MARKER="FRESH_OWNER_AUTHORIZED_R4: ${WP020_LIVE_EXECUTION_ID} @ ${GITHUB_SHA}"
FENCE_MARKER="EXECUTION_STARTED: ${WP020_LIVE_EXECUTION_ID}"
PASS_MARKER="LIVE_EXECUTION_PASS: ${WP020_LIVE_EXECUTION_ID}"
STOP_MARKER="LIVE_EXECUTION_STOPPED: ${WP020_LIVE_EXECUTION_ID}"
COMMENTS="$(gh issue view "${ISSUE_NUMBER}" --comments --json comments --jq '.comments[].body')"

if ! printf '%s\n' "${COMMENTS}" | grep -Fx "${AUTH_MARKER}" >/dev/null; then
  echo "STOP: exact fresh Owner R4 paid authorization marker missing for current main" >&2
  exit 1
fi
if printf '%s\n' "${COMMENTS}" | grep -Fx "${FENCE_MARKER}" >/dev/null; then
  echo "STOP: R4 one-shot execution fence already consumed" >&2
  exit 1
fi
if printf '%s\n' "${COMMENTS}" | grep -F "${PASS_MARKER}" >/dev/null || printf '%s\n' "${COMMENTS}" | grep -F "${STOP_MARKER}" >/dev/null; then
  echo "STOP: R4 execution identity already has terminal evidence" >&2
  exit 1
fi

case "${MODE}" in
  check)
    echo "Fresh Owner authorization present; R4 identity remains unused"
    ;;
  consume)
    gh issue comment "${ISSUE_NUMBER}" --body "${FENCE_MARKER}"
    echo "R4 one-shot execution fence consumed"
    ;;
  *)
    echo "Usage: $0 {check|consume}" >&2
    exit 2
    ;;
esac
