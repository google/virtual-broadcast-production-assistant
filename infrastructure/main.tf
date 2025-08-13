module "orchestrator" {
  source = "./modules/orchestrator"

  project_id    = var.project_id
  region        = var.region
  service_name  = var.orchestrator_service_name
  custom_domain = var.orchestrator_custom_domain
  dns_zone_name = var.dns_zone_name
  root_domain   = var.root_domain
}
