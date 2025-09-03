output "orchestrator_static_ip_address" {
  description = "The static IP address of the orchestrator load balancer."
  value       = module.orchestrator.static_ip_address
}

output "orchestrator_name_servers" {
  description = "The name servers for the orchestrator managed zone."
  value       = module.orchestrator.name_servers
}

output "orchestrator_nat_ip_address" {
  description = "The static outbound IP address of the orchestrator Cloud Run service."
  value       = module.orchestrator.nat_ip_address
}

output "frontend_lb_environments" {
  description = "The environments for the frontend load balancer."
  value       = module.frontend-lb.environments
}