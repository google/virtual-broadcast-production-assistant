resource "google_project_service" "artifactregistry" {
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "frontend_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "frontend-v2"
  description   = "Docker repository for the frontend-v2 service"
  format        = "DOCKER"
  depends_on    = [google_project_service.artifactregistry]
}

resource "google_clouddeploy_target" "frontend_targets" {
  for_each = var.frontend_environments
  project  = var.project_id
  location = var.region
  name     = "${each.value.service_name}-target"

  run {
    location = "projects/${var.project_id}/locations/${var.region}"
  }

  execution_configs {
    usages          = ["RENDER", "DEPLOY"]
    service_account = var.orchestrator_build_runner_service_account_email
  }
}

resource "google_clouddeploy_delivery_pipeline" "frontend_pipeline" {
  project  = var.project_id
  location = var.region
  name     = "frontend-v2-delivery"

  serial_pipeline {
    stages {
      target_id = google_clouddeploy_target.frontend_targets["staging"].name
      profiles  = ["staging"]
    }
    stages {
      target_id = google_clouddeploy_target.frontend_targets["stable"].name
      profiles  = ["stable"]
    }
  }

  depends_on = [google_clouddeploy_target.frontend_targets]
}
