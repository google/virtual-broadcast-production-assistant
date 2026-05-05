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

variable "frontend_environments" {
  description = "A map of environments for the frontend service."
  type = map(object({
    service_name    = string
    container_image = string
    custom_domain   = optional(string)
  }))
}

variable "orchestrator_dns_zone_name" {
  description = "The name of the Cloud DNS managed zone for the orchestrator."
  type        = string
}

variable "orchestrator_root_domain" {
  description = "The root domain for the DNS zone for the orchestrator."
  type        = string
}

variable "frontend_dns_zone_name" {
  description = "The name of the Cloud DNS managed zone for the frontend."
  type        = string
}

variable "frontend_root_domain" {
  description = "The root domain for the DNS zone for the frontend."
  type        = string
}

variable "orchestrator_service_account_email" {
  description = "The email of the service account for the orchestrator Cloud Run service."
  type        = string
}

variable "orchestrator_build_runner_service_account_email" {
  description = "The email of the service account for the orchestrator Cloud Build runner."
  type        = string
}