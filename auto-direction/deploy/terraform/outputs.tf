output "foh_proxy_uri" {
  value       = google_cloud_run_v2_service.foh_proxy.uri
  description = "The public URL of the FOH Proxy and Frontend"
}

output "director_proxy_uri" {
  value       = google_cloud_run_v2_service.director_proxy.uri
  description = "The public URL of the Director Proxy"
}
