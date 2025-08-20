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

variable "activity_agent_service_name" {
  description = "The name of the activity-agent Cloud Run service."
  type        = string
  default     = "activity-agent"
}

variable "agent_engine_service_name" {
  description = "The name of the Agent Engine service."
  type        = string
  default     = "agent-engine-service"
}

variable "agent_engine_vpc_network_name" {
  description = "The name of the VPC network for the Agent Engine."
  type        = string
  default     = "agent-engine-vpc"
}

variable "agent_engine_vpc_subnet_name" {
  description = "The name of the VPC subnetwork for the Agent Engine."
  type        = string
  default     = "agent-engine-subnet"
}

variable "reverse_proxy_service_name" {
  description = "The name of the Cloud Run reverse proxy service."
  type        = string
  default     = "reverse-proxy"
}

variable "reverse_proxy_container_image" {
  description = "The container image for the Cloud Run reverse proxy service."
  type        = string
  default     = "gcr.io/cloudrun/hello"
}

variable "agent_engine_url" {
  description = "The URL of the Agent Engine service."
  type        = string
  default     = ""
}

variable "agent_engine_url_secret_name" {
  description = "The name of the secret to store the Agent Engine URL."
  type        = string
  default     = "agent-engine-url"
}
