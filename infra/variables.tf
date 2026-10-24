variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type = string
  # 98% carbon-free energy, 30 gCO2eq/kWh grid intensity (Google, 2025 data,
  # cloud.google.com/sustainability/region-carbon, checked 2026-10-24).
  default     = "europe-north1"
  description = "Low-carbon region for Cloud Run, Firestore and Artifact Registry"
}

variable "gitlab_project_path" {
  type        = string
  description = "GitLab project path allowed to federate, e.g. gitlab-ai-hackathon/afterlife"
}

variable "gitlab_url" {
  type    = string
  default = "https://gitlab.com"
}

variable "service_name" {
  type    = string
  default = "shelf"
}

variable "unleash_url" {
  type        = string
  default     = ""
  description = "GitLab feature flags Unleash API URL (Deploy > Feature flags > Configure)"
}

variable "unleash_instance_id" {
  type        = string
  default     = ""
  description = "GitLab feature flags instance ID. Not a secret, but not a password either."
}

variable "gitlab_read_token_enabled" {
  type        = bool
  default     = false
  description = "Expose the afterlife-gitlab-read-token secret to Shelf. Set true after adding a secret version."
}
