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
  source = "./modules/backend/service-accounts"
}

module "build_triggers" {
  source                    = "./modules/build-triggers"
  terraform_bucket_name     = var.terraform_bucket
  websocket-service-account = module.backend_service_account.websocket-service-account-name
}

module "backend_websocket_server" {
  source          = "./modules/backend/websocket-server"
  project_id      = var.project_id
  region          = var.region
  container_image = "gcr.io/${var.project_id}/websocket-server:latest"
  service_account = module.backend_service_account.websocket-service-account-name
}

module "client_frontend" {
  source          = "./modules/client"
  project_id      = var.project_id
  region          = var.region
  container_image = "gcr.io/${var.project_id}/pastra-ui"
}


# VPC and Networking

module "networking" {
  source                          = "./modules/networking"
  region                          = var.region
  project                         = var.project_id
  vpc-name                        = "cuez-services"
  subnet-name                     = "cuez-services-subnet"
  vpc-access-connector-name       = "cuez-services-connector"
  vpc-access-connector-cidr-range = "10.8.0.0/28"
}

# VM for CUEZ Automator
module "cuez-automator" {
  source     = "./modules/cuez-automator"
  network    = module.networking.vpc-name
  subnetwork = module.networking.subnet-id
}

# Sofie
module "sofie" {
  source                         = "./modules/sofie"
  project                        = var.project_id
  region                         = var.region
  iap_support_email              = var.iap_support_email
  authorized_user_email          = var.iap_authorized_user_email
  vpc_name                       = module.networking.vpc-name
  vpc_self_link                  = module.networking.vpc-selflink
  subnetwork_self_link           = module.networking.subnet-id
  subnetwork_pods_range_name     = "pods-range"     # As defined in networking module
  subnetwork_services_range_name = "services-range" # As defined in networking module
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

variable "iap_support_email" {
  type        = string
  description = "The support email for IAP"
}

variable "iap_authorized_user_email" {
  type        = string
  description = "Email address of a user authorized to access Sofie via IAP"
}
