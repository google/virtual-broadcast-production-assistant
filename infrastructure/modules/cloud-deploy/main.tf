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

  dynamic "execution_configs" {
    for_each = var.execution_service_account_email != "" ? [1] : []
    content {
      usages          = ["RENDER", "DEPLOY"]
      service_account = var.execution_service_account_email
      worker_pool     = null
    }
  }

  custom_target {
    custom_target_type = google_clouddeploy_custom_target_type.run_target.id
  }
}

resource "google_clouddeploy_custom_target_type" "run_target" {
  project  = var.project_id
  location = var.region
  name     = "${var.target_name}-run-target-type"

  custom_actions {
    render_action = "render"
    deploy_action = "deploy"
  }
}
