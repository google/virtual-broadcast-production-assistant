variable "project_id" {
  description = "The project ID to deploy to."
  type        = string
}

variable "region" {
  description = "The region to deploy to."
  type        = string
}

variable "orchestrator_service_name" {
  description = "The name of the orchestrator Cloud Run service."
  type        = string
}

variable "orchestrator_custom_domain" {
  description = "The custom domain for the orchestrator service."
  type        = string
}

variable "dns_zone_name" {
  description = "The name of the Cloud DNS managed zone."
  type        = string
}

variable "root_domain" {
  description = "The root domain for the DNS zone."
  type        = string
}

variable "orchestrator_container_image" {
  description = "The container image for the orchestrator Cloud Run service."
  type        = string
}

variable "orchestrator_service_account_email" {
  description = "The email of the service account for the orchestrator Cloud Run service."
  type        = string
}

