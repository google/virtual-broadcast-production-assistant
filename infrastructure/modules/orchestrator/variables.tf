variable "project_id" {
  description = "The project ID to deploy to."
  type        = string
}

variable "region" {
  description = "The region to deploy to."
  type        = string
}

variable "environments" {
  description = "A map of environments to deploy to."
  type        = any
  default     = {}
}

variable "base_resource_name" {
  description = "The base name for resources."
  type        = string
}

variable "dns_zone_name" {
  description = "The name of the DNS managed zone."
  type        = string
}

variable "root_domain" {
  description = "The root domain for the DNS zone."
  type        = string
}

variable "service_account_email" {
  description = "The email of the service account for the Cloud Run service."
  type        = string
}

variable "vpc_network_name" {
  description = "The name of the VPC network."
  type        = string
  default     = "orchestrator-vpc"
}

variable "vpc_subnet_name" {
  description = "The name of the VPC subnetwork."
  type        = string
  default     = "orchestrator-subnet"
}

variable "build_runner_service_account_email" {
  description = "The email of the service account for the Cloud Build runner."
  type        = string
}