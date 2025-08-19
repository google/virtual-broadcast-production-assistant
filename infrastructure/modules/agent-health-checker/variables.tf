variable "project_id" {
  description = "The ID of the Google Cloud project."
  type        = string
}

variable "region" {
  description = "The region where resources will be deployed."
  type        = string
}

variable "cloud_run_job_service_account_email" {
  description = "The email of the service account for the Cloud Run Job."
  type        = string
}
