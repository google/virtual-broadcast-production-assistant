output "pipeline_id" {
  description = "The ID of the Cloud Deploy delivery pipeline."
  value       = google_clouddeploy_delivery_pipeline.pipeline.id
}

output "target_id" {
  description = "The ID of the Cloud Deploy target."
  value       = google_clouddeploy_target.target.id
}
