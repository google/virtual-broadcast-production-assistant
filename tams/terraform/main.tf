locals {
  project_prefix = var.short_project_name != "" ? var.short_project_name : var.project_id
  bucket_name    = "${local.project_prefix}-tams-objects"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable APIs
resource "google_project_service" "run_api" {
  service = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firestore_api" {
  service = "firestore.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage_api" {
  service = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry_api" {
  service = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Artifact Registry
resource "google_artifact_registry_repository" "tams_repo" {
  depends_on = [google_project_service.artifactregistry_api]
  location      = var.region
  repository_id = var.repository_name
  description   = "Docker repository for TAMS API"
  format        = "DOCKER"
}

# GCS Bucket
resource "google_storage_bucket" "tams_bucket" {
  depends_on = [google_project_service.storage_api]
  name          = local.bucket_name
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}

# Service Account
resource "google_service_account" "tams_sa" {
  account_id   = "tams-api-sa"
  display_name = "TAMS API Service Account"
}

# IAM Roles
resource "google_storage_bucket_iam_member" "storage_admin" {
  bucket = google_storage_bucket.tams_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.tams_sa.email}"
}

resource "google_project_iam_member" "datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.tams_sa.email}"
}

resource "google_project_iam_member" "token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:${google_service_account.tams_sa.email}"
}

# Firestore Database
resource "google_firestore_database" "tams_db" {
  depends_on = [google_project_service.firestore_api]
  project     = var.project_id
  name        = var.firestore_db_name
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

# Cloud Run Service
resource "google_cloud_run_service" "tams_api" {
  depends_on = [google_project_service.run_api, google_firestore_database.tams_db]
  name     = "tams-api"
  location = var.region

  template {
    spec {
      containers {
        image = var.image_name
        env {
          name  = "SERVICE_ACCOUNT_EMAIL"
          value = google_service_account.tams_sa.email
        }
        env {
          name  = "TAMS_BUCKET_NAME"
          value = google_storage_bucket.tams_bucket.name
        }
        env {
          name  = "FIRESTORE_DB_NAME"
          value = var.firestore_db_name
        }
      }
      service_account_name = google_service_account.tams_sa.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Firestore Composite Indexes
resource "google_firestore_index" "segments_start_index" {
  depends_on = [google_firestore_database.tams_db]
  project    = var.project_id
  database   = var.firestore_db_name
  collection = "segments"

  fields {
    field_path = "flow_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timerange_start"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "segments_end_index" {
  depends_on = [google_firestore_database.tams_db]
  project    = var.project_id
  database   = var.firestore_db_name
  collection = "segments"

  fields {
    field_path = "flow_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timerange_end"
    order      = "ASCENDING"
  }
}
