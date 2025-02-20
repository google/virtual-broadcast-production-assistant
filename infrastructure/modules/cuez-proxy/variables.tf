/**
 * Copyright 2023 Google LLC
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
