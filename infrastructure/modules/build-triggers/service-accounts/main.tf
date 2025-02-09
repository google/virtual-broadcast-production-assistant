/*
 Copyright 2025 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 */

data "google_project" "project" {}

# Trigger Service Accounts

resource "google_service_account" "cloud_build_runner" {
  account_id   = "cloud-build-runner"
  display_name = "Cloud Build Runner for Terraform Infrastructure"
  project      = data.google_project.project.project_id # or omit and use the provider's default
}


resource "google_project_iam_member" "cloud_build_runner_permissions" {
  project = data.google_project.project.project_id # or omit
  role    = "roles/cloudbuild.builds.builder"      # Core permission
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

# Optional but often necessary permissions (adjust to your needs):

resource "google_project_iam_member" "artifact_registry_writer" { # If pushing to Artifact Registry
  project = data.google_project.project.project_id                # or omit
  role    = "roles/artifactregistry.writer"                       # For pushing images
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "secret_manager_accessor" { # If accessing secrets
  project = data.google_project.project.project_id               # or omit
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

# ... other potential permissions (Cloud Functions deployer, etc.) as needed

output "cloud_build_runner_email" {
  value = google_service_account.cloud_build_runner.email
}
