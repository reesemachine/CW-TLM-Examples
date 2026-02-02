#!/usr/bin/env python3
"""
Drift detection: compare desired policies vs actual snapshot.

Usage:
  python tools/drift_check.py --desired endpoint-config/policies --actual endpoint-config/actual_snapshot.json

Snapshot format (example):
{
  "windows-compliance-baseline": {"settings": {...}, "platform": "windows"},
  "macos-security-baseline": {"settings": {...}, "platform": "macos"}
}
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple


@dataclass
class DriftItem:
    status: str
    desired: Any | None = None
    actual: Any | None = None


def load_desired(dir_path: Path) -> Dict[str, Dict[str, Any]]:
    desired: Dict[str, Dict[str, Any]] = {}
    for p in sorted(dir_path.rglob("*.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        name = obj.get("name")
        if not name:
            continue
        desired[name] = obj
    return desired


def load_actual(snapshot_path: Path) -> Dict[str, Dict[str, Any]]:
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def normalize_settings(settings: Any) -> Any:
    """
    Normalize settings to reduce false drift.
    - Sort dict keys deterministically
    - Leave lists as-is (your policies should treat list ordering as meaningful)
    """
    if isinstance(settings, dict):
        return {k: normalize_settings(settings[k]) for k in sorted(settings.keys())}
    if isinstance(settings, list):
        return [normalize_settings(x) for x in settings]
    return settings


def compare(desired: Dict[str, Dict[str, Any]], actual: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, DriftItem], int]:
    drift: Dict[str, DriftItem] = {}
    rc = 0

    # Missing or drifted
    for name, d in desired.items():
        a = actual.get(name)
        if a is None:
            drift[name] = DriftItem(status="missing_in_actual")
            rc = 1
            continue

        d_settings = normalize_settings(d.get("settings", {}))
        a_settings = normalize_settings(a.get("settings", {}))

        if d_settings != a_settings:
            drift[name] = DriftItem(
                status="settings_drift",
                desired=d_settings,
                actual=a_settings
            )
            rc = 1

    # Extra in actual
    for name in actual.keys():
        if name not in desired:
            drift[name] = DriftItem(status="extra_in_actual")
            rc = 1

    return drift, rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desired", required=True, type=Path)
    ap.add_argument("--actual", required=True, type=Path)
    args = ap.parse_args()

    if not args.desired.exists():
        raise SystemExit(f"Desired path not found: {args.desired}")
    if not args.actual.exists():
        raise SystemExit(f"Actual snapshot not found: {args.actual}")

    desired = load_desired(args.desired)
    actual = load_actual(args.actual)

    drift, rc = compare(desired, actual)

    out = {
        "count": len(drift),
        "drift": {k: v.__dict__ for k, v in drift.items()},
    }
    print(json.dumps(out, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
