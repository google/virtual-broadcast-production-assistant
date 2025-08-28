resource "google_clouddeploy_delivery_pipeline" "pipeline" {
  project  = var.project_id
  location = var.region
  name     = var.pipeline_name

  serial_pipeline {
    stages {
      target_id = var.target_name
      profiles  = []
    }
  }
}

resource "google_clouddeploy_target" "target" {
  project  = var.project_id
  location = var.region
  name     = var.target_name

  run {
    location = "projects/${var.project_id}/locations/${var.region}"

  }
}
