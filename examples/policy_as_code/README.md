# Policy-as-Code (Endpoint)

This example demonstrates a **source-of-truth** pattern for endpoint policy changes:
- Policies stored as JSON (or YAML) in `policies/`
- CI validates schema + naming + required metadata
- Drift checker compares "desired" vs "actual" (placeholder connector)

> In production you would connect to Jamf Pro / Intune / JumpCloud APIs.
