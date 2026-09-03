#!/usr/bin/env bash
# Delete generated export files older than 24 h (Section 12.2).
# Cron example (hourly):
#   0 * * * * /opt/knsb/scripts/cleanup_exports.sh
set -euo pipefail

OUTPUTS_DIR="${OUTPUTS_DIR:-./outputs}"
MAX_AGE_HOURS="${EXPORT_MAX_AGE_HOURS:-24}"

if [ ! -d "$OUTPUTS_DIR" ]; then
  echo "no outputs dir at $OUTPUTS_DIR — nothing to do"
  exit 0
fi

find "$OUTPUTS_DIR" -type f -mmin "+$((MAX_AGE_HOURS * 60))" -print -delete
echo "cleaned exports older than ${MAX_AGE_HOURS}h in ${OUTPUTS_DIR}"
