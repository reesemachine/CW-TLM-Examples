# Story Bank (Map TLM Requirements)

Each story is written as a **repeatable talk track**:
- **Goal**
- **Constraints / risks**
- **Your approach**
- **What you measured**
- **What you’d do differently**

---

## 1) IaC + change management for endpoint policies

**Goal:** eliminate configuration drift and “clickops” for Jamf/Intune policies  
**Constraints:** global fleet, security approvals, need fast iteration  
**Approach:**
- Treat policies as versioned artifacts (JSON/YAML)
- PR review + required approvals (Security + Endpoint Eng)
- CI validation (schema + lint + “blast radius” checks)
- Promotion across environments (dev → prod)
**Measured:** drift reductions, time-to-change, incident rate after changes

(See: `examples/policy_as_code/` + `tools/drift_check.py`)

---

## 2) Canary rings release for endpoint changes

**Goal:** safe rollout of configs, agents, and scripts  
**Constraints:** mixed OS, different geos, critical workflows  
**Approach:**
- Define rings (QA → Security → Early adopters → phased by region/BU)
- Gate promotions on telemetry and synthetic endpoint checks
- Rollback plan is first-class (last known good)
**Measured:** rollback frequency, mean time to detect, “breakage per release”

(See: `examples/canary_rings/`)

---

## 3) Android zero-touch enrollment automation

**Goal:** reduce staging time and errors for warehouse scanners  
**Approach:**
- Standardize COBO/COPE profiles
- Automate device assignment to config in zero-touch portal
- Inventory linking (asset tag, serial, owner/location)
**Measured:** time per device, enrollment failure rate

(See: `examples/android_zerotouch/`)

---

## 4) iOS internal app distribution automation (App Store Connect)

**Goal:** remove manual cert renewals + IPA upload work  
**Approach:**
- Use API token based auth (JWT) for App Store Connect
- Automate upload + release to B2B/internal channels
- Add validity checks and alerting before expirations
**Measured:** reduction in manual work, missed renewals, deployment lead time

(See: `examples/appstore_connect/`)

---

## 5) Firmware/BIOS automation pipeline

**Goal:** automate firmware + BIOS password rotation safely  
**Approach:**
- Wrap OEM tooling with a pipeline
- Stage in rings; require “health check” before promotion
- Produce audit logs + reports
**Measured:** patch compliance, “time-to-safe-rollout”, failure rate

(See: `examples/firmware_pipeline/`)
