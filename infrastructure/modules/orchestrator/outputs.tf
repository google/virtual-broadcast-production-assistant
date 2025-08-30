output "static_ip_address" {
  description = "The static IP address of the load balancer."
  value       = google_compute_global_address.static_ip.address
}

output "name_servers" {
  description = "The name servers for the managed zone."
  value       = try(google_dns_managed_zone.dns_zone[0].name_servers, [])
}

output "nat_ip_address" {
  description = "The static outbound IP address of the Cloud Run service."
  value       = google_compute_address.nat_ip.address
}

output "vpc_access_connector_id" {
  description = "The ID of the VPC Access Connector."
  value       = google_vpc_access_connector.connector.id
}

output "service_urls" {
  description = "The URLs of the deployed orchestrator services."
  value = {
    for key, service in google_cloud_run_v2_service.orchestrator_agent : key => service.uri
  }
}
