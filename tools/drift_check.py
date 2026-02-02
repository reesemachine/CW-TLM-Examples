#!/usr/bin/env python3
"""Drift detection (desired vs actual) — interview-friendly skeleton.

In production, `fetch_actual_state()` would call:
- Microsoft Graph (Intune)
- Jamf Pro API
- JumpCloud API
- Chef server, etc.

Here we model the pattern:
- Load desired policies from repo (JSON)
- Load a mocked "actual" snapshot (JSON)
- Report drift in a deterministic, CI-friendly way

Usage:
  python tools/drift_check.py --desired examples/policy_as_code/policies --actual examples/policy_as_code/actual_snapshot.example.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple

def load_desired(dir_path: Path) -> Dict[str, Any]:
    desired={}
    for p in dir_path.rglob("*.json"):
        obj=json.loads(p.read_text(encoding="utf-8"))
        desired[obj["name"]]=obj
    return desired

def load_actual(snapshot_path: Path) -> Dict[str, Any]:
    return json.loads(snapshot_path.read_text(encoding="utf-8"))

def compare(desired: Dict[str, Any], actual: Dict[str, Any]) -> Tuple[dict, int]:
    drift={}
    exit_code=0
    for name, d in desired.items():
        a = actual.get(name)
        if a is None:
            drift[name] = {"status": "missing_in_actual"}
            exit_code=1
            continue
        # Compare only 'settings' for demo (metadata differs across systems)
        if d.get("settings") != a.get("settings"):
            drift[name] = {
                "status": "settings_drift",
                "desired": d.get("settings"),
                "actual": a.get("settings"),
            }
            exit_code=1
    for name in actual.keys():
        if name not in desired:
            drift[name] = {"status": "extra_in_actual"}
            exit_code=1
    return drift, exit_code

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--desired", required=True, type=Path)
    ap.add_argument("--actual", required=True, type=Path)
    args=ap.parse_args()

    desired=load_desired(args.desired)
    actual=load_actual(args.actual)

    drift, rc = compare(desired, actual)
    print(json.dumps({"drift": drift, "count": len(drift)}, indent=2))
    return rc

if __name__ == "__main__":
    raise SystemExit(main())
