resource "google_service_account" "activity_agent_sa" {
  project      = var.project_id
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name}"
}

resource "google_project_iam_member" "activity_agent_sa_genai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.activity_agent_sa.email}"
}
