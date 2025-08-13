output "static_ip_address" {
  description = "The static IP address of the load balancer."
  value       = google_compute_global_address.static_ip.address
}

output "name_servers" {
  description = "The name servers for the managed zone."
  value       = google_dns_managed_zone.dns_zone.name_servers
}
