variable "project_id" {
  description = "The project ID to deploy to."
  type        = string
}

variable "region" {
  description = "The region to deploy to."
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
