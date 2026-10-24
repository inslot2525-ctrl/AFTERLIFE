locals {
  apis = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "monitoring.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "secretmanager.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# --- Artifact Registry ------------------------------------------------------

resource "google_artifact_registry_repository" "images" {
  repository_id = "afterlife"
  location      = var.region
  format        = "DOCKER"
  description   = "Shelf images, tagged by commit SHA"

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 30
    }
  }
  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30 days
    }
  }
  depends_on = [google_project_service.apis]
}

# --- Firestore --------------------------------------------------------------

resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.apis]
}

# --- Cloud Run --------------------------------------------------------------

resource "google_service_account" "runtime" {
  account_id   = "shelf-runtime"
  display_name = "Shelf Cloud Run runtime"
  depends_on   = [google_project_service.apis] # IAM API must be on first
}

resource "google_project_iam_member" "runtime_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Read-only GitLab token (read_api) for the graveyard's live timeline and
# verdicts. Terraform owns the secret, never its value: the version is added
# with `gcloud secrets versions add` (docs/runbook-om.md), so the token is in
# neither git nor Terraform state.
resource "google_secret_manager_secret" "gitlab_read_token" {
  secret_id = "afterlife-gitlab-read-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "runtime_reads_gitlab_token" {
  secret_id = google_secret_manager_secret.gitlab_read_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_cloud_run_v2_service" "shelf" {
  name                = var.service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.runtime.email
    scaling {
      min_instance_count = 0 # scale to zero between demos
      max_instance_count = 3
    }
    containers {
      # Placeholder until the first CI deploy; CI owns the image from then on.
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "UNLEASH_URL"
        value = var.unleash_url
      }
      env {
        name  = "UNLEASH_INSTANCE_ID"
        value = var.unleash_instance_id
      }
      env {
        name  = "UNLEASH_APP_NAME"
        value = "production"
      }
      env {
        name  = "AFTERLIFE_STORE"
        value = "firestore"
      }
      # Only once the secret has a version: Cloud Run refuses a revision whose
      # secret has none.
      dynamic "env" {
        for_each = var.gitlab_read_token_enabled ? [1] : []
        content {
          name = "AFTERLIFE_GITLAB_READ_TOKEN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.gitlab_read_token.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  # CI deploys new revisions and moves traffic (canary/promote/rollback).
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      traffic,
      client,
      client_version,
    ]
  }
  depends_on = [google_project_service.apis, google_secret_manager_secret_iam_member.runtime_reads_gitlab_token]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.shelf.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
