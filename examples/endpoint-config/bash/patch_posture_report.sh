#!/usr/bin/env bash
set -euo pipefail

echo "== Patch Posture Report =="

echo "macOS version:"
sw_vers

echo "Last softwareupdate history (best-effort):"
softwareupdate --history | head -n 25 || true

echo "Pending updates (best-effort):"
softwareupdate --list || true
