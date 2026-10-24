terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.10"
    }
  }
  # GitLab-managed Terraform state. Configure with -backend-config (see docs/runbook-om.md).
  backend "http" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
