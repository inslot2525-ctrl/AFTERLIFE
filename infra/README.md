# infra

Terraform for Google Cloud (owner: Om). Region `europe-north1`, chosen for its 98% carbon-free
energy. The setup, apply and CI variables are in [docs/runbook-om.md](../docs/runbook-om.md).

| File | Creates |
| --- | --- |
| `main.tf` | APIs, Artifact Registry (with cleanup), Firestore (native), Cloud Run `shelf` (min instances 0, public) |
| `wif.tf` | Workload Identity pool and GitLab OIDC provider, deploy SA (`run.admin`, `artifactregistry.writer`, `datastore.user`, `monitoring.viewer`), read-only plan SA |
| `outputs.tf` | Values to copy into GitLab CI/CD variables |

CI owns the running image and traffic split, so Terraform ignores them. The billing budget
alert is a one-time `gcloud billing budgets create`, documented in the runbook.
