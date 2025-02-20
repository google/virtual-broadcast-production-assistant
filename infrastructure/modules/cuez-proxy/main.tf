/**
 * Copyright 2023 Google LLC
 */

data "google_project" "project" {
}



resource "google_artifact_registry_repository" "cuez-custom-proxy" {
  location      = var.region
  repository_id = "cuez-custom-proxy"
  description   = "Managed by Terraform - Do not manually edit - cuez-custom-proxy repository"
  format        = "DOCKER"

  docker_config {
    immutable_tags = false
  }

  lifecycle {
    ignore_changes = [docker_config]
  }
}




# Create the Service Account to use with the cuez-custom-proxy Cloud Run service
resource "google_service_account" "cuez-custom-proxy-service-account" {
  account_id   = "${substr(var.cuez-custom-proxy-service-name, 0, 26)}-sa"
  display_name = "${title(substr(var.cuez-custom-proxy-service-name, 0, 26))} Backend Cloud Run SA"
  description  = "Service Account for the Cuez Custom Proxy Cloud Run Service"
}

# Give the Service Account the Service Account User role
resource "google_project_iam_member" "cuez-custom-proxy-sa-sa-user-role" {
  project = var.project
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cuez-custom-proxy-service-account.email}"
}



# Create the cuez-custom-proxy Cloud Run service with a placeholder container image
resource "google_cloud_run_v2_service" "cuez-custom-proxy-service" {
  name     = var.cuez-custom-proxy-service-name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  template {
    labels = {
      managed-by = "terraform"
    }
    scaling {
      min_instance_count = 0
    }
    vpc_access {
      connector = var.vpc-access-connector-id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    timeout         = "300s"
    service_account = google_service_account.cuez-custom-proxy-service-account.email
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      env {
        name  = "APP_PROJECT_ID"
        value = var.project
      }
      env {
        name  = "APP_REGION"
        value = var.region
      }
      env {
        name  = "APP_GEMINI_PROJECT_ID"
        value = var.project
      }
      env {
        name  = "APP_GEMINI_REGION"
        value = var.region
      }
      env {
        name  = "APP_CUEZ_API_HOST"
        value = var.cuez-app-api-host
      }
      env {
        name  = "APP_CUEZ_API_PORT"
        value = "7070"
      }
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "8",
          memory = "32Gi"
        }
      }
    }
    max_instance_request_concurrency = 80
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image
    ]
  }

}

# Allow the proxy Cloud Run service to be acessed by other services
data "google_iam_policy" "cuez-custom-proxy-invoker" {

  binding {
    role    = "roles/run.invoker"
    members = var.cuez-proxy-sa-access-list
  }
}


# Private connectivity to the managed zone

resource "google_dns_managed_zone" "psc-managed-zone" {

  name       = "run-app"
  dns_name   = "run.app."
  visibility = "private"

}

# Add an A record for the private.googleapis.com range in the managed zone
resource "google_dns_record_set" "internal-routing-a-record" {

  name         = "${google_cloud_run_v2_service.cuez-custom-proxy-service.uri}."
  managed_zone = google_dns_managed_zone.psc-managed-zone.name
  type         = "A"
  ttl          = 300
  rrdatas = [
    "10.3.0.5"
  ]
}
