output "cloud_run_url" {
  description = "The URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.app.uri
}

output "tailscale_router_instance_name" {
  description = "The name of the Tailscale Subnet Router VM"
  value       = google_compute_instance.tailscale_router.name
}

output "tailscale_ssh_command" {
  description = "Gcloud command to SSH into the Tailscale Subnet Router VM via IAP tunnel"
  value       = "gcloud compute ssh ${google_compute_instance.tailscale_router.name} --tunnel-through-iap --project ${var.project_id} --zone ${google_compute_instance.tailscale_router.zone}"
}



