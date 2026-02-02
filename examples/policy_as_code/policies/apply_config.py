#!/usr/bin/env python3
"""
Apply Jamf macOS configuration profiles from policy-as-code.

Usage:
  export JAMF_URL="https://your.jamfcloud.com"
  export JAMF_USER="apiuser"
  export JAMF_PASS="apipass"
  python tools/apply_config.py --ring qa --policies endpoint-config/policies --change-id CHG-1234

Notes:
- Uses Jamf Pro API token endpoint for auth: POST /api/v1/auth/token  [oai_citation:8‡Jamf Developer](https://developer.jamf.com/jamf-pro/reference/post_v1-auth-token?utm_source=chatgpt.com)
- Uses Classic API config profiles resource osxconfigurationprofiles (XML payloads).  [oai_citation:9‡Jamf Developer](https://developer.jamf.com/jamf-pro/reference/osxconfigurationprofiles?utm_source=chatgpt.com)
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

ALLOWED_RINGS = {"qa", "security", "early", "global"}

@dataclass
class ApplyResult:
    policy_name: str
    status: str  # applied | no_change | skipped | failed
    detail: str = ""

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_policies(policies_dir: Path) -> List[Dict[str, Any]]:
    policies: List[Dict[str, Any]] = []
    for p in sorted(policies_dir.rglob("*.json")):
        policies.append(json.loads(p.read_text(encoding="utf-8")))
    return policies

def is_policy_allowed_in_ring(policy: Dict[str, Any], ring: str) -> bool:
    scope = policy.get("scope") or {}
    supported = scope.get("supported_rings")
    if supported is None:
        return True
    return isinstance(supported, list) and ring in supported

class JamfAuth:
    def __init__(self, jamf_url: str, username: str, password: str) -> None:
        self.jamf_url = jamf_url.rstrip("/")
        self.username = username
        self.password = password
        self._token: Optional[str] = None

    def token(self) -> str:
        if self._token:
            return self._token
        endpoint = f"{self.jamf_url}/api/v1/auth/token"
        r = requests.post(endpoint, auth=(self.username, self.password), timeout=30)
        r.raise_for_status()
        data = r.json()
        tok = data.get("token")
        if not tok:
            raise RuntimeError("Jamf auth token response did not contain 'token'")
        self._token = tok
        return tok

def headers_json(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

def headers_xml(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/xml", "Accept": "application/xml"}

def build_classic_profile_xml(name: str, payload_xml: str) -> str:
    """
    Classic API expects XML body for osxconfigurationprofiles.
    This is a *minimal* wrapper. In real life you’d include scope, category, etc.
    """
    # Jamf Classic uses "os_x_configuration_profile" naming in some payloads.
    # Keeping minimal for portfolio/interview clarity.
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<os_x_configuration_profile>
  <general>
    <name>{name}</name>
    <description>Managed by policy-as-code</description>
  </general>
  <payloads><![CDATA[{payload_xml}]]></payloads>
</os_x_configuration_profile>
"""

class JamfClassicConnector:
    """
    Implements:
    - GET profile by name
    - PUT profile by name
    - POST create profile
    Based on Classic API osxconfigurationprofiles resource.  [oai_citation:10‡Jamf Developer](https://developer.jamf.com/jamf-pro/reference/osxconfigurationprofiles?utm_source=chatgpt.com)
    """
    def __init__(self, jamf_url: str, token: str) -> None:
        self.jamf_url = jamf_url.rstrip("/")
        self.token = token

    def get_profile_by_name(self, name: str) -> Optional[str]:
        url = f"{self.jamf_url}/JSSResource/osxconfigurationprofiles/name/{name}"
        r = requests.get(url, headers=headers_json(self.token), timeout=30)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        obj = r.json()

        # extract payload string (best-effort; Jamf’s response structure can vary)
        def scan(o: Any) -> Optional[str]:
            if isinstance(o, str) and o.strip().startswith("<?xml"):
                return o
            if isinstance(o, dict):
                for v in o.values():
                    got = scan(v)
                    if got:
                        return got
            if isinstance(o, list):
                for v in o:
                    got = scan(v)
                    if got:
                        return got
            return None

        return scan(obj)

    def update_profile_by_name(self, name: str, payload_xml: str) -> None:
        url = f"{self.jamf_url}/JSSResource/osxconfigurationprofiles/name/{name}"
        body = build_classic_profile_xml(name, payload_xml)
        r = requests.put(url, headers=headers_xml(self.token), data=body.encode("utf-8"), timeout=30)
        r.raise_for_status()

    def create_profile(self, name: str, payload_xml: str) -> None:
        url = f"{self.jamf_url}/JSSResource/osxconfigurationprofiles/id/0"
        body = build_classic_profile_xml(name, payload_xml)
        r = requests.post(url, headers=headers_xml(self.token), data=body.encode("utf-8"), timeout=30)
        r.raise_for_status()

def write_audit(out_path: Path, ring: str, change_id: str | None, results: List[ApplyResult]) -> None:
    payload = {
        "timestamp": now_utc(),
        "ring": ring,
        "change_id": change_id,
        "summary": {
            "applied": sum(1 for r in results if r.status == "applied"),
            "no_change": sum(1 for r in results if r.status == "no_change"),
            "skipped": sum(1 for r in results if r.status == "skipped"),
            "failed": sum(1 for r in results if r.status == "failed"),
        },
        "results": [r.__dict__ for r in results],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ring", required=True, help="qa|security|early|global")
    ap.add_argument("--policies", required=True, type=Path)
    ap.add_argument("--change-id", required=False)
    ap.add_argument("--audit-out", default=Path("out/audit_apply.json"), type=Path)
    args = ap.parse_args()

    ring = args.ring.strip().lower()
    if ring not in ALLOWED_RINGS:
        print(f"Invalid ring: {ring}. Allowed: {sorted(ALLOWED_RINGS)}")
        return 2

    if not args.policies.exists() or not args.policies.is_dir():
        print(f"Policies path not found or not a directory: {args.policies}")
        return 2

    jamf_url = os.environ.get("JAMF_URL", "").strip()
    jamf_user = os.environ.get("JAMF_USER", "").strip()
    jamf_pass = os.environ.get("JAMF_PASS", "").strip()
    if not jamf_url or not jamf_user or not jamf_pass:
        print("Missing env vars: JAMF_URL, JAMF_USER, JAMF_PASS are required.")
        return 2

    policies = load_policies(args.policies)

    # Auth + connector
    token = JamfAuth(jamf_url, jamf_user, jamf_pass).token()
    jamf = JamfClassicConnector(jamf_url, token)

    results: List[ApplyResult] = []

    for pol in policies:
        name = pol.get("name", "unknown")
        md = pol.get("metadata") or {}

        if md.get("emergency_use_only") is True:
            results.append(ApplyResult(name, "skipped", "emergency-use-only policy (break-glass)"))
            continue

        if not is_policy_allowed_in_ring(pol, ring):
            results.append(ApplyResult(name, "skipped", f"not allowed in ring={ring}"))
            continue

        if pol.get("platform") != "macos":
            results.append(ApplyResult(name, "skipped", "non-macOS policy (Jamf example applies macOS profiles only)"))
            continue

        settings = pol.get("settings") or {}
        if settings.get("type") != "jamf_configuration_profile":
            results.append(ApplyResult(name, "skipped", "macOS policy not marked as jamf_configuration_profile"))
            continue

        desired_xml = (settings.get("profile_plist_xml") or "").strip()
        if not desired_xml:
            results.append(ApplyResult(name, "failed", "missing settings.profile_plist_xml"))
            continue

        try:
            current_xml = jamf.get_profile_by_name(name)
            if current_xml is not None and current_xml.strip() == desired_xml:
                results.append(ApplyResult(name, "no_change", "Jamf payload already matches"))
                continue

            if current_xml is None:
                jamf.create_profile(name, desired_xml)
                results.append(ApplyResult(name, "applied", "created profile"))
            else:
                jamf.update_profile_by_name(name, desired_xml)
                results.append(ApplyResult(name, "applied", "updated profile"))

        except Exception as e:
            results.append(ApplyResult(name, "failed", str(e)))

    write_audit(args.audit_out, ring, args.change_id, results)

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
