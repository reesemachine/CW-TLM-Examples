#!/usr/bin/env bash
set -euo pipefail

echo "== Jamf Health Check =="

if [[ ! -x /usr/local/bin/jamf ]]; then
  echo "FAIL: /usr/local/bin/jamf not found"
  exit 2
fi

echo "Jamf version:"
/usr/local/bin/jamf -version || true

echo "Jamf recon (inventory update):"
/usr/local/bin/jamf recon || { echo "FAIL: recon failed"; exit 2; }

echo "Jamf policy run (forces management action):"
/usr/local/bin/jamf policy || { echo "FAIL: policy run failed"; exit 2; }

echo "OK: Jamf healthy"
