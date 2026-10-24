# infra

Terraform for Google Cloud (owner: Om). To create here:

- Cloud Run service `shelf` (min instances 0)
- Firestore in native mode
- Artifact Registry repository
- Workload Identity Federation pool and provider for GitLab OIDC
- Deploy service account with `run.admin`, `artifactregistry.writer`,
  `datastore.user`, `monitoring.viewer`
- A billing budget alert

Choose a low-carbon region and record why in `docs/sci.md`.
