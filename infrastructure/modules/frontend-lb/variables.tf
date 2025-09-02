variable "project_id" {
  description = "The project ID to deploy to."
  type        = string
}

variable "region" {
  description = "The region to deploy to."
  type        = string
}

variable "base_resource_name" {
  description = "The base name to use for shared resources."
  type        = string
}

variable "environments" {
  description = "A map of environments to deploy, e.g. stable, staging."
  type = map(object({
    service_name    = string
    container_image = string
    custom_domain   = optional(string)
  }))
}

variable "dns_zone_name" {
  description = "The name of the Cloud DNS managed zone."
  type        = string
}

variable "root_domain" {
  description = "The root domain for the DNS zone."
  type        = string
}
