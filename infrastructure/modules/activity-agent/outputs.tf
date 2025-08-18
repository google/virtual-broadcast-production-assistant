output "service_account_email" {
  description = "The email of the service account created for the activity agent."
  value       = google_service_account.activity_agent_sa.email
}
