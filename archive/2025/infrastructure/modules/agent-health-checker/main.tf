resource "google_project_service" "cloudscheduler" {
  project            = var.project_id
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

resource "google_service_account" "agent_health_checker" {
  account_id   = "agent-health-checker"
  display_name = "Agent Health Checker Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "agent_health_checker_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.agent_health_checker.email}"
}

resource "google_project_iam_member" "agent_health_checker_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.agent_health_checker.email}"
}

resource "google_project_iam_member" "agent_health_checker_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.agent_health_checker.email}"
}

resource "google_cloud_run_v2_job" "agent_health_checker" {
  name                = "agent-health-checker"
  location            = var.region
  project             = var.project_id
  deletion_protection = false

  template {
    template {
      service_account = google_service_account.agent_health_checker.email
      dynamic "vpc_access" {
        for_each = var.vpc_access_connector_id != null ? [1] : []
        content {
          connector = var.vpc_access_connector_id
          egress    = "ALL_TRAFFIC"
        }
      }
      containers {
        image = format("%s-docker.pkg.dev/%s/cloud-run-source-deploy/agent-health-check:%s", var.region, var.project_id, var.image_tag)
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
    ]
  }
}

resource "google_cloud_scheduler_job" "agent_health_check_scheduler" {
  name     = "agent-health-check-scheduler"
  schedule = "* * * * *" # Every minute
  region   = "europe-west1"
  project  = var.project_id

  http_target {
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/agent-health-checker:run"
    http_method = "POST"
    oauth_token {
      service_account_email = google_service_account.agent_health_checker.email
    }
  }

  depends_on = [google_project_service.cloudscheduler]
}
