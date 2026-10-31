#!/usr/bin/env bash
# Runs one setup and saves every request to results/round<N>/k6-measured-data/ (test runs: results/test/).
#
#   ./loadtest/run.sh <profile> <round> <setup>   e.g.  ./loadtest/run.sh restricted 1 cpu-1024
#   ./loadtest/run.sh test <setup>                20 s check with 1 user (not study data)
#
# Profiles: restricted (fits the current AWS limit) or standard (the proposal's levels).
# The users per setup are defined in run.js.
set -euo pipefail
cd "$(dirname "$0")/.."

# Fail early with a clear message if something is missing.
if ! command -v k6 >/dev/null 2>&1; then
  echo "k6 isn't installed. Install it with 'brew install k6' (Mac) or 'winget install k6' (Windows), then try again." >&2
  exit 1
fi
if [ ! -f loadtest/urls.json ]; then
  echo "loadtest/urls.json is missing. Ask the repo owner for it (it's private and not in git)." >&2
  exit 1
fi

usage() {
  echo "Usage: ./loadtest/run.sh <restricted|standard> <1|2|3> <setup>   e.g. ./loadtest/run.sh restricted 1 cpu-1024" >&2
  echo "       ./loadtest/run.sh test <setup>" >&2
  exit 1
}
if [ "${1:-}" = "test" ]; then
  [ $# -eq 2 ] || usage
  setup="$2"
  mkdir -p results/test
  out="results/test/test-${setup}.jsonl"
  rm -f "$out"
  args=(-e MODE=test)
else
  [ $# -eq 3 ] || usage
  profile="$1"
  round="$2"
  setup="$3"
  case "$profile" in restricted|standard) ;; *) echo "Profile must be restricted or standard (got '$profile')" >&2; exit 1 ;; esac
  case "$round" in 1|2|3) ;; *) echo "Round must be 1, 2 or 3 (got '$round')" >&2; exit 1 ;; esac
  mkdir -p "results/round${round}/k6-measured-data"
  out="results/round${round}/k6-measured-data/${profile}-r${round}-${setup}.jsonl"
  if [ -e "$out" ]; then
    echo "$out already exists. Delete it first if you really want to redo this run." >&2
    exit 1
  fi
  args=(-e PROFILE="$profile")
  # k6's web dashboard, saved as an HTML report next to the results. The live page is
  # off (port -1): an open browser tab on it keeps k6 from exiting and stalls the round.
  # Set DASHBOARD=0 to skip the report.
  if [ "${DASHBOARD:-1}" != "0" ]; then
    export K6_WEB_DASHBOARD=true
    export K6_WEB_DASHBOARD_PORT=-1
    export K6_WEB_DASHBOARD_EXPORT="${out%.jsonl}.html"
  fi
fi

echo "Setup $setup -> $out"
k6 run --quiet --log-format raw --console-output "$out" -e SETUP="$setup" "${args[@]}" loadtest/run.js
echo "Saved $(wc -l < "$out" | tr -d ' ') requests to $out"
if [ -n "${K6_WEB_DASHBOARD_EXPORT:-}" ] && [ -f "$K6_WEB_DASHBOARD_EXPORT" ]; then
  echo "Dashboard report: $K6_WEB_DASHBOARD_EXPORT (open it in a browser)"
fi
