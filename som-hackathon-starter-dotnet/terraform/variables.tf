variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "The region to deploy resources to"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "The name of the Managed Kafka cluster"
  type        = string
  default     = "som-kafka-cluster"
}

variable "image_url" {
  description = "The Docker image URL for the application"
  type        = string
}

variable "repository_name" {
  description = "The name of the Artifact Registry repository"
  type        = string
  default     = "som-repo"
}

variable "kafka_bootstrap_servers" {
  description = "The bootstrap servers for the Managed Kafka cluster"
  type        = string
  default     = ""
}

variable "cloudbuild_bucket" {
  description = "The name of the Cloud Build source bucket"
  type        = string
}

variable "github_owner" {
  description = "The GitHub owner of the repository"
  type        = string
  default     = "jgrayston"
}
