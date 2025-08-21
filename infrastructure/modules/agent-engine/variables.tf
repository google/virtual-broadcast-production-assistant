variable "project_id" {
  description = "The ID of the Google Cloud project."
  type        = string
}

variable "region" {
  description = "The Google Cloud region for the resources."
  type        = string
}

variable "agent_engine_service_name" {
  description = "The name of the Agent Engine service."
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

variable "agent_engine_url_secret_name" {
  description = "The name of the secret to store the Agent Engine URL."
  type        = string
  default     = "agent-engine-url"
}

variable "cloud_build_runner_service_account_email" {
  description = "The email of the service account for the Cloud Build runner that needs access to secrets."
  type        = string
}
