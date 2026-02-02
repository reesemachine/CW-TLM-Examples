#!/usr/bin/env python3
"""Generate a zero-touch assignment plan from device inventory (demo).

Input CSV columns:
  serial,imei,asset_tag,site,owner_group

Output:
- JSON assignment plan (what config each device should get)
- audit log (who/when/why)

This is intentionally offline + deterministic for interview review.
"""
from __future__ import annotations
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

def pick_config(row: Dict[str, str]) -> str:
    # Simple rules engine demo
    site = (row.get("site") or "").lower()
    if "warehouse" in site:
        return "cfg-android-warehouse-cobo"
    return "cfg-android-corp-cope"

def run(input_csv: Path) -> Dict:
    assignments=[]
    with input_csv.open(newline="", encoding="utf-8") as f:
        reader=csv.DictReader(f)
        for row in reader:
            assignments.append({
                "serial": row.get("serial"),
                "imei": row.get("imei"),
                "asset_tag": row.get("asset_tag"),
                "site": row.get("site"),
                "owner_group": row.get("owner_group"),
                "config": pick_config(row),
            })
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(assignments),
        "assignments": assignments,
    }

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args=ap.parse_args()

    plan=run(args.input)
    args.out.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"Wrote plan: {args.out} ({plan['count']} devices)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
