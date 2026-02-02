# Firmware / BIOS Automation Pipeline (Pattern)

Wrap OEM tooling in an auditable, ring-based workflow:
- detect models + current firmware versions
- decide target versions
- stage rollout in rings
- produce logs + reports

This example provides:
- `firmware_plan.py` – create a plan from an inventory snapshot
- `run_health_check.ps1` – placeholder preflight checks
