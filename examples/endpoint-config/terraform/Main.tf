terraform {
  required_version = ">= 1.6.0"
}

variable "ring" {
  type        = string
  description = "qa|security|early|global"
}

variable "change_id" {
  type        = string
  description = "Change/CAB ticket id"
  default     = ""
}

variable "repo_root" {
  type        = string
  description = "Path to repo root (where endpoint-config/ and tools/ exist)"
  default     = "."
}

locals {
  policies_dir = "${var.repo_root}/endpoint-config/policies"
  audit_out    = "${var.repo_root}/out/terraform_audit_apply_${var.ring}.json"
}

# Compute a stable hash of all policy files; if any policy changes, Terraform sees a new trigger.
data "external" "policy_hash" {
  program = ["bash", "-lc", <<EOT
set -euo pipefail
cd "${var.repo_root}"
python3 - <<'PY'
import hashlib, glob
h=hashlib.sha256()
for p in sorted(glob.glob("endpoint-config/policies/**/*.json", recursive=True)):
    with open(p, "rb") as f:
        h.update(f.read())
print('{"hash":"%s"}' % h.hexdigest())
PY
EOT
  ]
}

# Lint + drift check as "test gates" (fails fast)
resource "null_resource" "validate" {
  triggers = {
    policy_hash = data.external.policy_hash.result.hash
  }

  provisioner "local-exec" {
    command = <<EOT
set -euo pipefail
cd "${var.repo_root}"
python3 tools/policy_lint.py endpoint-config/policies
python3 tools/drift_check.py --desired endpoint-config/policies --actual endpoint-config/actual_snapshot.example.json
EOT
  }
}

# Apply to a ring (idempotent)
resource "null_resource" "apply_ring" {
  depends_on = [null_resource.validate]

  triggers = {
    policy_hash = data.external.policy_hash.result.hash
    ring        = var.ring
    change_id   = var.change_id
  }

  provisioner "local-exec" {
    command = <<EOT
set -euo pipefail
cd "${var.repo_root}"
test -n "${var.ring}"
# For non-QA rings, enforce change ticket (mirrors CoreWeave-style change control)
if [ "${var.ring}" != "qa" ] && [ -z "${var.change_id}" ]; then
  echo "change_id required for ring=${var.ring}" >&2
  exit 1
fi

# Jamf creds expected in env: JAMF_URL/JAMF_USER/JAMF_PASS
python3 tools/apply_config.py \
  --ring "${var.ring}" \
  --policies endpoint-config/policies \
  --change-id "${var.change_id}" \
  --audit-out "${local.audit_out}"

echo "Wrote audit: ${local.audit_out}"
EOT
  }
}

output "policy_hash" {
  value = data.external.policy_hash.result.hash
}

output "audit_log" {
  value = local.audit_out
}
