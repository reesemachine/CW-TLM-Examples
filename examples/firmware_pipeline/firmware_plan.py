#!/usr/bin/env python3
"""Create a firmware update plan from an inventory snapshot (demo).

Input JSON:
[
  {"asset_tag":"AT-0001","vendor":"Dell","model":"Latitude 7440","bios":"1.2.0"},
  ...
]

Output JSON:
- which devices need updates to a target baseline
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from packaging.version import Version

TARGETS = {
    ("Dell", "Latitude 7440"): "1.6.0",
    ("HP", "EliteBook 840 G10"): "1.5.2",
    ("Lenovo", "T14 Gen 4"): "1.3.0",
}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args=ap.parse_args()

    inv=json.loads(args.inventory.read_text(encoding="utf-8"))
    plan=[]
    for d in inv:
        key=(d.get("vendor"), d.get("model"))
        target = TARGETS.get(key)
        if not target:
            continue
        if Version(d.get("bios")) < Version(target):
            plan.append({
                "asset_tag": d.get("asset_tag"),
                "vendor": d.get("vendor"),
                "model": d.get("model"),
                "current_bios": d.get("bios"),
                "target_bios": target,
                "ring": "qa",  # start safe
            })
    args.out.write_text(json.dumps({"count": len(plan), "plan": plan}, indent=2), encoding="utf-8")
    print(f"Wrote firmware plan: {args.out} ({len(plan)} devices)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
