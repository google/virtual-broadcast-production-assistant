variable "project_id" {
  description = "The project ID to deploy to."
  type        = string
}

variable "region" {
  description = "The region to deploy to."
  type        = string
}

variable "image_tag" {
  description = "The tag of the docker image to deploy."
  type        = string
  default     = "latest"
}

variable "vpc_access_connector_id" {
  description = "The ID of the VPC Access Connector to use for the Cloud Run Job."
  type        = string
  default     = null
}
