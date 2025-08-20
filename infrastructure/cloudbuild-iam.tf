
variable "cloud_build_runner_service_account_email" {
  description = "The email of the service account for the Cloud Build runner."
  type        = string
  default     = "cloud-build-runner@peerless-kit-450316-g1.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "cloud_build_runner_artifactregistry_admin" {
  project = var.project_id
  role    = "roles/artifactregistry.admin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_artifactregistry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_cloudbuild_builds_builder" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_cloudbuild_builds_editor" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_compute_instance_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_compute_network_user" {
  project = var.project_id
  role    = "roles/compute.networkUser"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_compute_security_admin" {
  project = var.project_id
  role    = "roles/compute.securityAdmin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_dns_admin" {
  project = var.project_id
  role    = "roles/dns.admin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_iam_security_admin" {
  project = var.project_id
  role    = "roles/iam.securityAdmin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_iam_service_account_admin" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_iam_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_logging_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_secretmanager_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_serviceusage_service_usage_admin" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageAdmin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_vpcaccess_admin" {
  project = var.project_id
  role    = "roles/vpcaccess.admin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_project_iam_member" "cloud_build_runner_aiplatform_admin" {
  project = var.project_id
  role    = "roles/aiplatform.admin"
  member  = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}
