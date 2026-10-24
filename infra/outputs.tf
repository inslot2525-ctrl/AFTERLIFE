# Copy these into GitLab CI/CD variables (docs/runbook-om.md).

output "WIF_PROVIDER" {
  value = google_iam_workload_identity_pool_provider.gitlab.name
}

output "DEPLOY_SA" {
  value = google_service_account.deploy.email
}

output "TF_PLAN_SA" {
  value = google_service_account.plan.email
}

output "AR_REPO" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "SHELF_URL" {
  value = google_cloud_run_v2_service.shelf.uri
}
