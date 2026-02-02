# Canary Rings Release Pattern (Endpoint Configs)

This demonstrates a safe release management model for endpoint changes:
- Define **rings** (QA → Security → Early adopters → phased rollout)
- Run validation before promotion
- Require telemetry / synthetic checks before widening blast radius
- Keep rollback easy: “last known good” is always available

Artifacts:
- `.github/workflows/canary-rings.yml` – example GitHub Actions workflow
- `examples/canary_rings/promote.py` – promotion controller (demo)
