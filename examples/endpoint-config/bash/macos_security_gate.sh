#!/usr/bin/env bash
set -euo pipefail

fail() { echo "FAIL: $1"; exit 1; }

# FileVault gate
fv="$(fdesetup status | tr '[:upper:]' '[:lower:]')"
echo "FileVault: $fv"
echo "$fv" | grep -q "filevault is on" || fail "FileVault not enabled"

# Firewall gate
fw="$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate | tr '[:upper:]' '[:lower:]')"
echo "Firewall: $fw"
echo "$fw" | grep -q "enabled" || fail "Firewall not enabled"

echo "OK: security gates passed"
