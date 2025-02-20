/**
 * Copyright 2023 Google LLC
 */

resource "google_project_service" "enable-cloud-resource-manager-api" {

  project = var.project_id
  service = "cloudresourcemanager.googleapis.com"

  timeouts {
    create = "15m"
    update = "15m"
  }

  disable_dependent_services = false
  disable_on_destroy         = false

}

resource "google_project_service" "enable-required-apis" {

  for_each = toset([
    "aiplatform.googleapis.com",
    "dns.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "run.googleapis.com",
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "servicenetworking.googleapis.com",
    "secretmanager.googleapis.com",
    "vpcaccess.googleapis.com"
  ])
  project = var.project_id
  service = each.value

  timeouts {
    create = "15m"
    update = "15m"
  }

  disable_dependent_services = false
  disable_on_destroy         = false

  depends_on = [
    google_project_service.enable-cloud-resource-manager-api
  ]

}
