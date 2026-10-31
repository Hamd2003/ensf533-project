#!/usr/bin/env bash
# Runs a whole round as the proposal describes: all 11 setups once each, in a new
# random order, each 30 s warm-up + 120 s measurement. Takes about 35 minutes.
#
#   ./loadtest/round.sh restricted 1   round 1 at the restricted user counts (fits the current AWS limit)
#   ./loadtest/round.sh standard 1     round 1 at the proposal's user counts (needs the raised limit)
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

SETUPS=(
  api-512 api-1024 api-1769
  cpu-512 cpu-1024 cpu-1769
  data-512 data-1024 data-1769
  cpu-1024-low cpu-1024-high
)
PAUSE_S=${PAUSE_S:-40} # idle gap between runs, so the AWS export summary shows each run as its own row

if [ $# -ne 2 ]; then
  echo "Usage: ./loadtest/round.sh <restricted|standard> <1|2|3>   e.g. ./loadtest/round.sh restricted 1" >&2
  exit 1
fi
profile="$1"
round="$2"
case "$profile" in restricted|standard) ;; *) echo "Profile must be restricted or standard (got '$profile')" >&2; exit 1 ;; esac
case "$round" in 1|2|3) ;; *) echo "Round must be 1, 2 or 3 (got '$round')" >&2; exit 1 ;; esac
prefix="${profile}-r${round}"
label="${profile}-round${round}"
dir="results/round${round}/k6-measured-data"
mkdir -p "$dir"

# A round must start clean, so it never stops halfway because a file already exists.
existing=$(ls "$dir/${prefix}"-*.jsonl 2>/dev/null || true)
if [ -n "$existing" ]; then
  echo "$profile round $round already has results:" >&2
  echo "$existing" >&2
  echo "Delete them first if you really want to redo the whole round." >&2
  exit 1
fi

# Shuffle (Fisher-Yates) so every round uses a new random order.
order=("${SETUPS[@]}")
for ((i = ${#order[@]} - 1; i > 0; i--)); do
  j=$((RANDOM % (i + 1)))
  tmp=${order[i]}; order[i]=${order[j]}; order[j]=$tmp
done

started=$(TZ=America/Edmonton date '+%Y-%m-%d %-I:%M%p' | tr 'APM' 'apm')
order_file="$dir/${prefix}-order.txt"
{
  echo "$profile round $round started $started (Calgary)"
  echo "run setup start_utc"
} > "$order_file"

echo "$profile round $round started $started (Calgary). Order:"
printf '  %s\n' "${order[@]}"
echo

n=0
for setup in "${order[@]}"; do
  n=$((n + 1))
  echo "=== Run $n/${#order[@]}: $setup ($(TZ=America/Edmonton date '+%H:%M:%S')) ==="
  echo "$n $setup $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$order_file"
  ./loadtest/run.sh "$profile" "$round" "$setup"

  out="$dir/${prefix}-${setup}.jsonl"
  failed=$(grep -c '"valid":false' "$out" || true)
  throttled=$(grep -c '"status":429' "$out" || true)
  if [ "$failed" -gt 0 ]; then
    echo "!!! $failed failed requests ($throttled of them throttled, 429). Tell the repo owner."
  else
    echo "OK: no failed requests."
  fi

  if [ "$n" -lt "${#order[@]}" ]; then
    echo "Pausing ${PAUSE_S} s before the next run..."
    sleep "$PAUSE_S"
  fi
  echo
done

echo "$profile round $round finished. Order and start times: $order_file"
echo "In 10 minutes, run GitHub Actions -> export-aws-data with:"
echo "  start = $started"
echo "  label = $label"
