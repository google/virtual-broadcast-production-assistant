variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "region" {
  type        = string
  description = "The GCP region"
  default     = "europe-west1"
}

variable "short_project_name" {
  type        = string
  description = "A short name for the project to be used as a prefix for globally unique resources like GCS buckets. Defaults to project_id if not set."
  default     = ""
}

variable "firestore_db_name" {
  type        = string
  description = "The name of the Firestore database"
  default     = "tams-db"
}

variable "repository_name" {
  type        = string
  description = "The name of the Artifact Registry repository"
  default     = "tams-repo"
}

variable "image_name" {
  type        = string
  description = "The Docker image name for the TAMS API"
  default     = "gcr.io/cloudrun/hello" # Default to dummy image
}
