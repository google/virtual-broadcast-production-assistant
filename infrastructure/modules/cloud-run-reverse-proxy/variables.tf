
variable "project_id" {
  description = "The ID of the Google Cloud project."
  type        = string
}

variable "region" {
  description = "The Google Cloud region for the resources."
  type        = string
}

variable "service_name" {
  description = "The name of the Cloud Run service."
  type        = string
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
}

variable "vpc_subnet_name" {
  description = "The name of the VPC subnetwork."
  type        = string
}

variable "agent_engine_url" {
  description = "The URL of the Agent Engine service."
  type        = string
}
