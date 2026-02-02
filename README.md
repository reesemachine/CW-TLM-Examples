# CW-TLM-Examples

Examples/portfolio of endpoint engineering patterns 

> ⚠️ note: these examples are **reference implementations only**. Using **placeholders** for tenant IDs, secrets, and API tokens.

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

- `docs/` –  story bank
- `examples/` – code examples (self-contained)
- `tools/` – reusable utilities (drift check, policy linting, report generation)
- `.github/workflows/` – CI examples (lint, unit tests, staged release)

## License

MIT
