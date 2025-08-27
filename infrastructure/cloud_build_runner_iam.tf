resource "google_project_iam_member" "cloud_build_runner_logging_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:cloud-build-runner@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "cloud_build_runner_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:cloud-build-runner@${var.project_id}.iam.gserviceaccount.com"
}

data "google_project" "project" {
  project_id = var.project_id
}

resource "google_service_account_iam_member" "cloud_build_runner_compute_sa_user" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${data.google_project.project.number}-compute@developer.gserviceaccount.com"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:cloud-build-runner@${var.project_id}.iam.gserviceaccount.com"
}