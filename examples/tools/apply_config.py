#!/usr/bin/env python3
"""
Apply endpoint config policies to a target ring (demo).

Usage:
  python tools/apply_config.py --ring qa --policies endpoint-config/policies --change-id CHG-1234
  python tools/apply_config.py --ring global --artifact dist/endpoint-config.tgz --change-id CHG-1234

This is vendor-neutral. Replace the `Connector` methods with real APIs:
- Intune: Microsoft Graph
- Jamf Pro: Jamf API
- FleetDM: Fleet API
"""

from __future__ import annotations

import argparse
import json
import os
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ALLOWED_RINGS = {"qa", "security", "early", "global"}


@dataclass
class ApplyResult:
    policy_name: str
    status: str  # applied|skipped|no_change|failed
    detail: str = ""


class Connector:
    """
    Placeholder connector. Implement these with real vendor calls.

    Key expectation: idempotency.
    - "apply_policy" should produce no changes if the target already matches.
    - returning "no_change" is good and expected.
    """

    def __init__(self, token: str):
        self.token = token

    def get_current_policy(self, name: str) -> Optional[Dict[str, Any]]:
        # In production: GET policy from API
        return None

    def apply_policy(self, policy: Dict[str, Any]) -> ApplyResult:
        # In production: create/update policy via API
        return ApplyResult(policy_name=policy["name"], status="applied", detail="demo apply (replace with API call)")

    def rollback_to_last_known_good(self, ring: str, reason: str) -> None:
        # In production: revert ring to previous artifact version
        pass


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_artifact(artifact_path: Path, workdir: Path) -> Path:
    """
    Extract artifact (.tgz) into workdir and return extracted policies dir path.
    Expected structure inside tar:
      endpoint-config/policies/*.json
    """
    workdir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(artifact_path, "r:gz") as tf:
        tf.extractall(path=workdir)
    policies_dir = workdir / "endpoint-config" / "policies"
    if not policies_dir.exists():
        raise RuntimeError(f"Artifact missing expected path: {policies_dir}")
    return policies_dir


def load_policies(policies_dir: Path) -> List[Dict[str, Any]]:
    policies: List[Dict[str, Any]] = []
    for p in sorted(policies_dir.rglob("*.json")):
        policies.append(json.loads(p.read_text(encoding="utf-8")))
    return policies


def is_policy_allowed_in_ring(policy: Dict[str, Any], ring: str) -> bool:
    scope = policy.get("scope") or {}
    supported = scope.get("supported_rings")
    if supported is None:
        return True  # default allow if not specified
    if isinstance(supported, list):
        return ring in supported
    return False


def apply_all(conn: Connector, policies: List[Dict[str, Any]], ring: str) -> List[ApplyResult]:
    results: List[ApplyResult] = []

    for pol in policies:
        name = pol.get("name", "unknown")
        if not is_policy_allowed_in_ring(pol, ring):
            results.append(ApplyResult(policy_name=name, status="skipped", detail=f"not allowed in ring={ring}"))
            continue

        # Break-glass policies must never be applied via normal ring rollouts
        md = pol.get("metadata") or {}
        if md.get("emergency_use_only") is True and ring != "break-glass":
            results.append(ApplyResult(policy_name=name, status="skipped", detail="emergency-use-only policy"))
            continue

        # Idempotency seam:
        current = conn.get_current_policy(name)
        desired_settings = pol.get("settings", {})

        if current is not None:
            current_settings = current.get("settings", {})
            if current_settings == desired_settings:
                results.append(ApplyResult(policy_name=name, status="no_change", detail="already compliant"))
                continue

        # Apply/update
        try:
            results.append(conn.apply_policy(pol))
        except Exception as e:
            results.append(ApplyResult(policy_name=name, status="failed", detail=str(e)))

    return results


def write_audit_log(out_path: Path, ring: str, change_id: str | None, results: List[ApplyResult]) -> None:
    payload = {
        "timestamp": now_utc(),
        "ring": ring,
        "change_id": change_id,
        "results": [r.__dict__ for r in results],
        "summary": {
            "applied": sum(1 for r in results if r.status == "applied"),
            "no_change": sum(1 for r in results if r.status == "no_change"),
            "skipped": sum(1 for r in results if r.status == "skipped"),
            "failed": sum(1 for r in results if r.status == "failed"),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ring", required=True, help="qa|security|early|global")
    ap.add_argument("--change-id", required=False)
    ap.add_argument("--policies", type=Path, required=False, help="Directory containing JSON policies")
    ap.add_argument("--artifact", type=Path, required=False, help="Packaged .tgz artifact containing policies")
    ap.add_argument("--audit-out", type=Path, default=Path("out/audit_apply.json"))
    args = ap.parse_args()

    ring = args.ring.strip().lower()
    if ring not in ALLOWED_RINGS:
        raise SystemExit(f"Invalid ring: {ring}. Allowed: {sorted(ALLOWED_RINGS)}")

    if not args.policies and not args.artifact:
        raise SystemExit("You must provide either --policies <dir> or --artifact <tgz>")

    token = os.environ.get("ENDPOINT_API_TOKEN", "")
    if not token:
        # For interview repo: allow empty token but clearly warn.
        print("WARN: ENDPOINT_API_TOKEN not set (demo mode).")

    # Resolve policies directory
    policies_dir: Path
    tmp_dir = Path(".tmp_apply")
    if args.artifact:
        if not args.artifact.exists():
            raise SystemExit(f"Artifact not found: {args.artifact}")
        policies_dir = extract_artifact(args.artifact, tmp_dir)
    else:
        if not args.policies or not args.policies.exists():
            raise SystemExit(f"Policies path not found: {args.policies}")
        policies_dir = args.policies

    policies = load_policies(policies_dir)
    conn = Connector(token=token)

    results = apply_all(conn, policies, ring)

    write_audit_log(args.audit_out, ring=ring, change_id=args.change_id, results=results)

    failed = [r for r in results if r.status == "failed"]
    print(f"Applied={sum(1 for r in results if r.status=='applied')}, "
          f"NoChange={sum(1 for r in results if r.status=='no_change')}, "
          f"Skipped={sum(1 for r in results if r.status=='skipped')}, "
          f"Failed={len(failed)}")

    if failed:
        for r in failed:
            print(f"FAIL: {r.policy_name}: {r.detail}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
