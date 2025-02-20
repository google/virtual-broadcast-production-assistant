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


data "google_project" "default" {}

variable "terraform_bucket_name" {
  type        = string
  description = "The name of the Terraform state bucket"
}


# Trigger Service Account

resource "google_service_account" "cloud_build_runner" {
  project      = data.google_project.default.project_id
  account_id   = "cloud-build-runner"
  display_name = "Cloud Build Runner for Terraform Infrastructure"
}

output "cloud_build_runner_email" {
  value = google_service_account.cloud_build_runner.email
}

# This will allow the main service account to create triggers.
resource "google_project_iam_member" "cloudbuild_trigger_create" {
  project = data.google_project.default.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "iam_security_admin" {
  project = data.google_project.default.project_id # or omit
  role    = "roles/iam.securityAdmin"              # Core permission
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "cloudrun_admin" {
  project = data.google_project.default.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

# Allow permission for the Cloud Build Runner to actAs the websocket SA
resource "google_service_account_iam_member" "cloud_build_runner_impersonate" {
  service_account_id = "projects/${data.google_project.default.project_id}/serviceAccounts/${var.websocket-service-account}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "cloudbuild_trigger_sa_admin" {
  project = data.google_project.default.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}


resource "google_project_iam_member" "cloud_build_runner_permissions" {
  project = data.google_project.default.project_id # or omit
  role    = "roles/cloudbuild.builds.builder"      # Core permission
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_storage_bucket_iam_member" "cloud_build_runner_state_bucket_access" {
  bucket = var.terraform_bucket_name   # The name of the Terraform state bucket
  role   = "roles/storage.objectAdmin" # The specific role needed
  member = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "service_usage_admin" {
  project = data.google_project.default.project_id
  role    = "roles/serviceusage.serviceUsageAdmin"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "artifact_registry_writer" { # If pushing to Artifact Registry
  project = data.google_project.default.project_id                # or omit
  role    = "roles/artifactregistry.writer"                       # For pushing images
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "secret_manager_accessor" { # If accessing secrets
  project = data.google_project.default.project_id               # or omit
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

# Networking permissions

resource "google_project_iam_member" "network_user" {
  project = data.google_project.default.project_id
  role    = "roles/compute.networkUser"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "vpc_access_admin" {
  project = data.google_project.default.project_id
  role    = "roles/vpcaccess.admin"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "compute_security_admin" {
  project = data.google_project.default.project_id
  role    = "roles/compute.securityAdmin"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}


# resource "google_project_iam_member" "compute_xpn_admin" { # Only if using XPN/Shared VPC
#   project = data.google_project.default.project_id
#   role    = "roles/compute.xpnAdmin"
#   member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
# }


# I think these two are needed for the runner based of the Hashicorp examples
resource "google_project_iam_member" "act_as" {
  project = data.google_project.default.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "logs_writer" {
  project = data.google_project.default.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "compute_instance_admin" {
  project = data.google_project.default.project_id
  role    = "roles/compute.instanceAdmin"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

resource "google_project_iam_member" "compute_global_address" {
  project = data.google_project.default.project_id
  role    = "roles/compute.networkUser"
  member  = "serviceAccount:${google_service_account.cloud_build_runner.email}"
}

# The below is disabled because I spent a while getting no where with it
# It kept saying invalid argument no matter what I did. Most be something to do
# with Gen 2 Cloud Build. We don't have an official example of a Gen 2 trigger vai
# terraform.

# resource "google_cloudbuild_trigger" "infra" {
#   name = "terraform-infra"
#   # description = "(Managed by Terraform, do not edit) - Trigger for terraform"


#   repository_event_config {
#     repository = var.cloud-source-repositories-repo-name
#     push {
#       branch = "main"
#     }
#   }

#   location = "europe-west1"
#   project  = data.google_project.default.project_id
#   filename = "build/infrastructure/cloudbuild.yaml"
#   # included_files = [
#   #   "infrastrucutre"
#   # ]
#   service_account = google_service_account.cloud_build_runner.id

#   # depends_on = [
#   #   google_project_iam_member.act_as,
#   #   google_project_iam_member.logs_writer
#   # ]
# }
