variable "project_id" {
  description = "The project ID to deploy to."
  type        = string
}

variable "service_name" {
  description = "The name of the Cloud Run service."
  type        = string
  default     = "activity-agent"
}
