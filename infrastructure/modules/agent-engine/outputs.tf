
output "agent_engine_url_secret_id" {
  description = "The ID of the secret containing the Agent Engine URL."
  value       = google_secret_manager_secret.agent_engine_url.secret_id
}
