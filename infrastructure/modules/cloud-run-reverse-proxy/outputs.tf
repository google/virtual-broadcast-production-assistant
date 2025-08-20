
output "reverse_proxy_neg_id" {
  description = "The ID of the Network Endpoint Group for the reverse proxy."
  value       = google_compute_region_network_endpoint_group.serverless_neg.id
}
