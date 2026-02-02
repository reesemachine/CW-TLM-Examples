#!/usr/bin/env python3
"""
Policy linter for endpoint policy-as-code.

Usage:
  python tools/policy_lint.py endpoint-config/policies

Exit codes:
  0 = OK
  1 = lint errors
  2 = usage / path errors
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+].+)?$")


@dataclass
class LintError:
    path: str
    message: str


REQUIRED_TOP_LEVEL = {"name", "platform", "version", "metadata", "settings"}
REQUIRED_METADATA = {"owner", "approver_groups", "change_ticket_required", "risk_level", "rollout_strategy"}

ALLOWED_PLATFORMS = {"windows", "macos", "linux", "ios", "android", "cross-platform"}
ALLOWED_RISK = {"low", "medium", "high", "critical"}
ALLOWED_ROLLOUT = {"ringed", "manual-only"}

ALLOWED_RINGS = {"qa", "security", "early", "global"}

# Policies with this name are treated as special and require strict handling.
BREAK_GLASS_NAMES = {"break-glass-exception", "break_glass_exception"}


def load_json(path: Path) -> Tuple[Dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, str(e)


def _expect(cond: bool, path: Path, msg: str, errors: List[LintError]) -> None:
    if not cond:
        errors.append(LintError(str(path), msg))


def lint_policy(path: Path, policy: Dict[str, Any]) -> List[LintError]:
    errors: List[LintError] = []

    # Required fields
    missing = REQUIRED_TOP_LEVEL - set(policy.keys())
    _expect(not missing, path, f"Missing top-level fields: {sorted(missing)}", errors)
    if missing:
        return errors  # can't continue reliably

    name = policy.get("name")
    platform = policy.get("platform")
    version = policy.get("version")
    metadata = policy.get("metadata") or {}
    settings = policy.get("settings") or {}
    scope = policy.get("scope") or {}
    telemetry = policy.get("telemetry_expectations") or {}

    # Types
    _expect(isinstance(name, str) and name.strip(), path, "name must be a non-empty string", errors)
    _expect(platform in ALLOWED_PLATFORMS, path, f"platform must be one of {sorted(ALLOWED_PLATFORMS)}", errors)
    _expect(isinstance(version, str) and SEMVER_RE.match(version) is not None, path, "version must be semver (e.g., 1.2.3)", errors)
    _expect(isinstance(metadata, dict), path, "metadata must be an object", errors)
    _expect(isinstance(settings, dict), path, "settings must be an object", errors)

    # Metadata required keys
    missing_meta = REQUIRED_METADATA - set(metadata.keys())
    _expect(not missing_meta, path, f"Missing metadata fields: {sorted(missing_meta)}", errors)

    # Metadata value checks (only if present)
    if "risk_level" in metadata:
        _expect(metadata["risk_level"] in ALLOWED_RISK, path, f"metadata.risk_level must be one of {sorted(ALLOWED_RISK)}", errors)
    if "rollout_strategy" in metadata:
        _expect(metadata["rollout_strategy"] in ALLOWED_ROLLOUT, path, f"metadata.rollout_strategy must be one of {sorted(ALLOWED_ROLLOUT)}", errors)
    if "approver_groups" in metadata:
        _expect(isinstance(metadata["approver_groups"], list) and metadata["approver_groups"], path, "metadata.approver_groups must be a non-empty list", errors)

    # Scope sanity
    if scope:
        _expect(isinstance(scope, dict), path, "scope must be an object", errors)

        supported_rings = scope.get("supported_rings")
        if supported_rings is not None:
            _expect(isinstance(supported_rings, list) and supported_rings, path, "scope.supported_rings must be a non-empty list", errors)
            if isinstance(supported_rings, list):
                invalid = [r for r in supported_rings if r not in ALLOWED_RINGS]
                _expect(not invalid, path, f"scope.supported_rings contains invalid ring(s): {invalid}", errors)

    # Telemetry thresholds sanity: values between 0 and 1
    if telemetry:
        _expect(isinstance(telemetry, dict), path, "telemetry_expectations must be an object", errors)
        for k, v in telemetry.items():
            if isinstance(v, (int, float)):
                _expect(0 <= float(v) <= 1, path, f"telemetry_expectations.{k} must be between 0 and 1", errors)

    # Break-glass guardrails
    if isinstance(name, str) and name in BREAK_GLASS_NAMES:
        # Must be manual-only and critical
        if isinstance(metadata, dict):
            _expect(metadata.get("rollout_strategy") == "manual-only", path, "break-glass must have rollout_strategy=manual-only", errors)
            _expect(metadata.get("risk_level") == "critical", path, "break-glass must have risk_level=critical", errors)
            _expect(metadata.get("emergency_use_only") is True, path, "break-glass must set metadata.emergency_use_only=true", errors)

        # Must have TTL / auto-expire
        tc = policy.get("time_constraints") or {}
        _expect(isinstance(tc, dict) and tc.get("auto_expire") is True, path, "break-glass must enable time_constraints.auto_expire=true", errors)
        _expect(isinstance(tc.get("max_duration_minutes"), int) and 1 <= tc["max_duration_minutes"] <= 240,
                path, "break-glass max_duration_minutes must be an int between 1 and 240", errors)

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2

    root = Path(sys.argv[1])
    if not root.exists() or not root.is_dir():
        print(f"Path not found or not a directory: {root}")
        return 2

    all_errors: List[LintError] = []
    json_files = list(root.rglob("*.json"))
    if not json_files:
        print(f"No JSON policies found under: {root}")
        return 2

    for p in sorted(json_files):
        obj, err = load_json(p)
        if err:
            all_errors.append(LintError(str(p), f"Invalid JSON: {err}"))
            continue
        all_errors.extend(lint_policy(p, obj or {}))

    if all_errors:
        for e in all_errors:
            print(f"{e.path}: {e.message}")
        print(f"\nFAIL: {len(all_errors)} issue(s)")
        return 1

    print(f"OK: {len(json_files)} policy file(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
