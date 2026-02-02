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


def _expect(cond: bool, path: Path, msg:_
