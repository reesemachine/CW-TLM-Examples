#!/usr/bin/env python3
"""
Jamf-aware policy linter for endpoint policy-as-code.

Usage:
  python tools/policy_lint.py endpoint-config/policies

Exit codes:
  0 = OK
  1 = lint errors
  2 = usage/path errors
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+].+)?$")

REQUIRED_TOP = {"name", "platform", "version", "metadata", "settings"}
REQUIRED_META = {"owner", "approver_groups", "change_ticket_required", "risk_level", "rollout_strategy"}

ALLOWED_PLATFORMS = {"windows", "macos", "linux", "ios", "android", "cross-platform"}
ALLOWED_RISK = {"low", "medium", "high", "critical"}
ALLOWED_ROLLOUT = {"ringed", "manual-only"}
ALLOWED_RINGS = {"qa", "security", "early", "global"}

BREAK_GLASS_NAMES = {"break-glass-exception", "break_glass_exception"}


@dataclass
class LintError:
    path: str
    message: str


def load_json(path: Path) -> Tuple[Dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, str(e)


def expect(cond: bool, path: Path, msg: str, errors: List[LintError]) -> None:
    if not cond:
        errors.append(LintError(str(path), msg))


def lint_policy(path: Path, p: Dict[str, Any]) -> List[LintError]:
    errors: List[LintError] = []

    missing = REQUIRED_TOP - set(p.keys())
    expect(not missing, path, f"Missing top-level fields: {sorted(missing)}", errors)
    if missing:
        return errors

    name = p.get("name")
    platform = p.get("platform")
    version = p.get("version")
    metadata = p.get("metadata") or {}
    settings = p.get("settings") or {}
    scope = p.get("scope") or {}

    expect(isinstance(name, str) and name.strip(), path, "name must be a non-empty string", errors)
    expect(platform in ALLOWED_PLATFORMS, path, f"platform must be one of {sorted(ALLOWED_PLATFORMS)}", errors)
    expect(isinstance(version, str) and SEMVER_RE.match(version) is not None, path, "version must be semver (e.g., 1.2.3)", errors)
    expect(isinstance(metadata, dict), path, "metadata must be an object", errors)
    expect(isinstance(settings, dict), path, "settings must be an object", errors)

    missing_meta = REQUIRED_META - set(metadata.keys())
    expect(not missing_meta, path, f"Missing metadata fields: {sorted(missing_meta)}", errors)

    if "risk_level" in metadata:
        expect(metadata["risk_level"] in ALLOWED_RISK, path, f"metadata.risk_level must be one of {sorted(ALLOWED_RISK)}", errors)
    if "rollout_strategy" in metadata:
        expect(metadata["rollout_strategy"] in ALLOWED_ROLLOUT, path, f"metadata.rollout_strategy must be one of {sorted(ALLOWED_ROLLOUT)}", errors)

    # ring scoping
    supported_rings = scope.get("supported_rings")
    if supported_rings is not None:
        expect(isinstance(supported_rings, list) and supported_rings, path, "scope.supported_rings must be a non-empty list", errors)
        if isinstance(supported_rings, list):
            invalid = [r for r in supported_rings if r not in ALLOWED_RINGS]
            expect(not invalid, path, f"scope.supported_rings contains invalid ring(s): {invalid}", errors)

    # Jamf-specific: if platform macos and this is meant to be a config profile,
    # require an XML payload.
    if platform == "macos":
        # you can choose your own flag; this one is explicit
        if settings.get("type") == "jamf_configuration_profile":
            xml_payload = settings.get("profile_plist_xml")
            expect(isinstance(xml_payload, str) and xml_payload.strip().startswith("<?xml"),
                   path,
                   "macOS Jamf profile must include settings.profile_plist_xml containing plist XML",
                   errors)

    # break-glass guardrails
    if isinstance(name, str) and name in BREAK_GLASS_NAMES:
        expect(metadata.get("rollout_strategy") == "manual-only", path, "break-glass must have rollout_strategy=manual-only", errors)
        expect(metadata.get("risk_level") == "critical", path, "break-glass must have risk_level=critical", errors)
        expect(metadata.get("emergency_use_only") is True, path, "break-glass must set metadata.emergency_use_only=true", errors)

        tc = p.get("time_constraints") or {}
        expect(isinstance(tc, dict), path, "break-glass must include time_constraints object", errors)
        if isinstance(tc, dict):
            expect(tc.get("auto_expire") is True, path, "break-glass must enable time_constraints.auto_expire=true", errors)
            mdur = tc.get("max_duration_minutes")
            expect(isinstance(mdur, int) and 1 <= mdur <= 240, path, "break-glass max_duration_minutes must be int 1..240", errors)

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2

    root = Path(sys.argv[1])
    if not root.exists() or not root.is_dir():
        print(f"Path not found or not a directory: {root}")
        return 2

    files = sorted(root.rglob("*.json"))
    if not files:
        print(f"No JSON policies found under: {root}")
        return 2

    all_errors: List[LintError] = []
    for f in files:
        obj, err = load_json(f)
        if err:
            all_errors.append(LintError(str(f), f"Invalid JSON: {err}"))
            continue
        all_errors.extend(lint_policy(f, obj or {}))

    if all_errors:
        for e in all_errors:
            print(f"{e.path}: {e.message}")
        print(f"\nFAIL: {len(all_errors)} issue(s)")
        return 1

    print(f"OK: {len(files)} policy file(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
