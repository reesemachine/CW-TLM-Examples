#!/usr/bin/env python3
"""Simple policy-as-code linter.

This intentionally avoids vendor-specific API calls.
It checks:
- required fields
- metadata completeness
- basic type validation

Usage:
  python tools/policy_lint.py examples/policy_as_code/policies
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REQUIRED_TOP = {"name", "platform", "metadata", "settings"}
REQUIRED_META = {"owner", "approver_group", "change_ticket_required"}

def lint_file(p: Path) -> list[str]:
    errors=[]
    try:
        data=json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"{p}: invalid JSON: {e}"]
    missing = REQUIRED_TOP - set(data.keys())
    if missing:
        errors.append(f"{p}: missing top-level fields: {sorted(missing)}")
        return errors
    meta = data.get("metadata", {})
    mm = REQUIRED_META - set(meta.keys())
    if mm:
        errors.append(f"{p}: missing metadata fields: {sorted(mm)}")
    if not isinstance(meta.get("approver_group", []), list):
        errors.append(f"{p}: metadata.approver_group must be a list")
    if not isinstance(data.get("settings", {}), dict):
        errors.append(f"{p}: settings must be an object/dict")
    return errors

def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])
    if not root.exists():
        print(f"Path not found: {root}")
        return 2
    errors=[]
    for p in root.rglob("*.json"):
        errors.extend(lint_file(p))
    if errors:
        print("\n".join(errors))
        return 1
    print(f"OK: {root}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
