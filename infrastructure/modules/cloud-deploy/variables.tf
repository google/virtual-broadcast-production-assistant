variable "project_id" {
  description = "The ID of the project in which to provision resources."
  type        = string
}

variable "region" {
  description = "The region in which to provision resources."
  type        = string
}

variable "pipeline_name" {
  description = "The name of the Cloud Deploy delivery pipeline."
  type        = string
}

variable "target_name" {
  description = "The name of the Cloud Deploy target."
  type        = string
}

variable "execution_service_account_email" {
  description = "The email of the service account to use for Cloud Deploy execution."
  type        = string
  default     = ""
}
