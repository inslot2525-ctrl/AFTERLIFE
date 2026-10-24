# GitLab OIDC -> Workload Identity Federation. CI never holds a key.

resource "google_iam_workload_identity_pool" "gitlab" {
  workload_identity_pool_id = "gitlab"
  display_name              = "GitLab CI"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "gitlab" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.gitlab.workload_identity_pool_id
  workload_identity_pool_provider_id = "gitlab-com"
  display_name                       = "gitlab.com"

  attribute_mapping = {
    "google.subject"            = "assertion.sub"
    "attribute.project_path"    = "assertion.project_path"
    "attribute.ref"             = "assertion.ref"
    "attribute.ref_type"        = "assertion.ref_type"
    "attribute.ref_protected"   = "assertion.ref_protected"
    "attribute.pipeline_source" = "assertion.pipeline_source"
  }
  # Only our project may federate. Hardening once the spike passes: add
  # "&& assertion.ref_protected == 'true'" after confirming MR pipelines on a
  # protected afterlife/* source branch carry ref_protected=true.
  attribute_condition = "assertion.project_path == '${var.gitlab_project_path}'"

  oidc {
    issuer_uri = var.gitlab_url
    # No allowed_audiences: the default is this provider's full resource name,
    # which is what id_tokens aud is set to in ci/templates.yml.
  }
}

# --- deploy SA: what CI acts as ---------------------------------------------

resource "google_service_account" "deploy" {
  account_id   = "afterlife-deploy"
  display_name = "AFTERLIFE CI deploy"
}

resource "google_project_iam_member" "deploy" {
  for_each = toset([
    "roles/run.admin",
    "roles/artifactregistry.writer",
    "roles/datastore.user",
    "roles/monitoring.viewer",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

# Deploying a revision that runs as shelf-runtime requires actAs on it.
resource "google_service_account_iam_member" "deploy_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_service_account_iam_member" "gitlab_impersonates_deploy" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.gitlab.name}/attribute.project_path/${var.gitlab_project_path}"
}

# --- plan SA: read-only, used by terraform plan on MRs ----------------------

resource "google_service_account" "plan" {
  account_id   = "afterlife-tf-plan"
  display_name = "AFTERLIFE terraform plan (read-only)"
}

resource "google_project_iam_member" "plan" {
  for_each = toset(["roles/viewer", "roles/iam.securityReviewer"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.plan.email}"
}

resource "google_service_account_iam_member" "gitlab_impersonates_plan" {
  service_account_id = google_service_account.plan.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.gitlab.name}/attribute.project_path/${var.gitlab_project_path}"
}
