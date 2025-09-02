variable "project_id" {
  description = "The project ID to deploy to."
  type        = string
}

variable "region" {
  description = "The region to deploy to."
  type        = string
}

variable "orchestrator_environments" {
  description = "A map of environments for the orchestrator service."
  type = map(object({
    service_name    = string
    container_image = string
    custom_domain   = optional(string)
  }))
}

variable "orchestrator_base_resource_name" {
  description = "The original service name of the orchestrator, used to construct resource names and preserve existing infrastructure like static IPs. e.g., 'orchestrator-agent'."
  type        = string
}

variable "frontend_container_image_stable" {
  description = "The container image for the stable frontend service."
  type        = string
}

variable "frontend_container_image_staging" {
  description = "The container image for the staging frontend service."
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

variable "orchestrator_service_account_email" {
  description = "The email of the service account for the orchestrator Cloud Run service."
  type        = string
}

