variable "project_id" {
  description = "The project ID to deploy to."
  type        = string
  default     = "peerless-kit-450316-g1"
}

variable "region" {
  description = "The region to deploy to."
  type        = string
  default     = "europe-west1"
}

variable "service_name" {
  description = "The name of the Cloud Run service."
  type        = string
  default     = "orchestrator-agent"
}

variable "custom_domain" {
  description = "The custom domain for the service."
  type        = string
  # e.g. orchestrator.your-domain.com
  default     = ""
}

variable "dns_zone_name" {
  description = "The name of the Cloud DNS managed zone. Must be a unique name within the project, e.g. 'your-domain-com'."
  type        = string
  default     = ""
}

variable "root_domain" {
  description = "The root domain for the DNS zone."
  type        = string
  # e.g. your-domain.com
  default     = ""
}

variable "container_image" {
  description = "The container image for the Cloud Run service."
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



variable "reverse_proxy_neg_id" {
  description = "The ID of the Network Endpoint Group for the reverse proxy."
  type        = string
}

