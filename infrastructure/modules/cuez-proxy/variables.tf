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

variable "cuez-custom-proxy-service-name" {
  description = "Name of the subdomain to use with the cuez-custom-proxy"
  type        = string
}

variable "vpc-access-connector-id" {
  description = "The ID of the VPC Access Connector"
  type        = string
}

variable "cuez-app-api-host" {
  description = "The host for Automator"
  type        = string
}

variable "cuez-proxy-sa-access-list" {
  description = "A list of Service Accounts that can access the proxy"
  type        = list(string)
}
