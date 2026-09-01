variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID where resources will be deployed"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "The Google Cloud region to deploy resources in"
}

variable "container_image_url" {
  type        = string
  description = "The fully qualified URL of the container image in Artifact Registry or GCR"
}
