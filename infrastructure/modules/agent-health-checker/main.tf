resource "google_cloud_run_v2_job" "agent_health_checker" {
  name     = "agent-health-checker"
  location = var.region
  project  = var.project_id

  template {
    template {
      containers {
        image = "gcr.io/${var.project_id}/agent-health-checker"
      }
    }
  }
}

resource "google_cloud_scheduler_job" "agent_health_check_scheduler" {
  name     = "agent-health-check-scheduler"
  schedule = "* * * * *" # Every minute
  region   = var.region
  project  = var.project_id

  http_target {
    uri = "https://run.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.agent_health_checker.name}:run"
    http_method = "POST"
    oauth_token {
      service_account_email = var.cloud_run_job_service_account_email
    }
  }
}
