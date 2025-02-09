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


terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" # Or latest compatible version
    }
  }


}

provider "google" {
  project = var.project_id
  region  = var.region
}

terraform {
  backend "gcs" {
    prefix = "terraform"
  }
}

module "backend_service_account" {
  source       = "./modules/backend/service-accounts"
  name         = "backend-sa"
  display_name = "Backend Service Account"
}

module "build_service_accounts" {
  source = "./modules/build-triggers/service-accounts" # Path adjusted
}

module "build_triggers" {
  source = "./modules/build-triggers"
}

# module "backend_secrets" {
#   source     = "./modules/secret-manager"
#   project_id = var.project_id
#   secrets = {
#     GOOGLE_API_KEY = {
#       value = var.gemini_api_key # Pass this as a variable
#     },
#     OPENWEATHER_API_KEY = {           # Include other secrets similarly
#       value = var.openweather_api_key # Pass this as a variable
#     }
#     # Add other secrets as needed...
#   }
# }


# resource "google_project_iam_member" "pastra_backend_secret_accessor" {
#   project = var.project_id
#   role    = "roles/secretmanager.secretAccessor"
#   member  = "serviceAccount:${module.pastra_backend_service_account.email}"
# }

variable "project_id" {
  type        = string
  description = "The GCP project ID"
}

variable "region" {
  type        = string
  description = "The GCP region for Cloud Run"
  default     = "europe-west1"
}

variable "terraform_bucket" {
  type        = string
  description = "Terraform bucket name"
}
