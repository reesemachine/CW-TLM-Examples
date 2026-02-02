# CW-TLM-Examples

A small, interview-friendly portfolio of endpoint engineering patterns aligned to CoreWeave’s **Endpoint Engineering Tech-Lead Manager (TLM)** role.

> ⚠️ Safety note: these examples are **reference implementations**. They use **placeholders** for tenant IDs, secrets, and API tokens. Do **not** commit real secrets.

## What’s inside

- **IaC + Change Control**: policy-as-code layout, validation, drift detection
- **Canary/Rings release**: staged rollout workflow pattern with guardrails
- **Android Zero-touch**: enrollment + device inventory patterns
- **App Store Connect distribution**: automated internal distribution pattern (B2B)
- **Firmware/BIOS automation**: pipeline pattern (wrap OEM tooling)

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python tools/drift_check.py --help
```

## Repo layout

- `docs/` – interview cheat sheet + story bank
- `examples/` – code examples (each is self-contained)
- `tools/` – reusable utilities (drift check, policy linting, report generation)
- `.github/workflows/` – CI examples (lint, unit tests, staged release)

## License

MIT
