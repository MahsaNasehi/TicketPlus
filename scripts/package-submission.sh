#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
output=${1:-"$root/submission/ticketplus.zip"}

mkdir -p "$(dirname "$output")"
cd "$root"

zip -q -r "$output" . \
  -x '.git/*' \
  -x '.agents/*' \
  -x '.codex/*' \
  -x '.terraform/*' \
  -x '*.tfstate*' \
  -x '*/__pycache__/*' \
  -x 'docs/product/*' \
  -x 'reports/coverage/*.cover' \
  -x 'submission/*'

printf 'Created %s\n' "$output"
printf 'Add the team-maintained Product Vision, Risk Analysis, and Jira exports before final submission.\n'
