output "orchestrator_static_ip_address" {
  description = "The static IP address of the orchestrator load balancer."
  value       = module.orchestrator.static_ip_address
}

output "orchestrator_name_servers" {
  description = "The name servers for the orchestrator managed zone."
  value       = module.orchestrator.name_servers
}
