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


variable "project" {
  type        = string
  description = "The GCP Project name to use for the deployments"
}

variable "region" {
  type        = string
  description = "The GCP Region to use for the deployments"
}

variable "iap_support_email" {
  description = "The support email for IAP configuration"
  type        = string
}

variable "authorized_user_email" {
  description = "Email address of a user authorized to access Sofie via IAP"
  type        = string
}

variable "vpc_name" {
  type        = string
  description = "The name of the VPC network for the GKE cluster."
}

variable "vpc_self_link" {
  type        = string
  description = "The self-link of the VPC network for the GKE cluster and firewall rules."
}

variable "subnetwork_self_link" {
  type        = string
  description = "The self-link of the subnetwork for the GKE cluster."
}

variable "subnetwork_pods_range_name" {
  type        = string
  description = "The name of the secondary IP range in the subnetwork for GKE pods."
}

variable "subnetwork_services_range_name" {
  type        = string
  description = "The name of the secondary IP range in the subnetwork for GKE services."
}
