provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  frontend_environments_with_websocket = {
    for key, env in var.frontend_environments : key => merge(env, {
      websocket_url = "wss://${var.orchestrator_environments[key].custom_domain}"
    })
  }
}

module "orchestrator" {
  source = "./modules/orchestrator"

  project_id            = var.project_id
  region                = var.region
  environments          = var.orchestrator_environments
  base_resource_name    = var.orchestrator_base_resource_name
  dns_zone_name         = var.orchestrator_dns_zone_name
  root_domain           = var.orchestrator_root_domain
  service_account_email = var.orchestrator_service_account_email
  build_runner_service_account_email = var.orchestrator_build_runner_service_account_email
}

module "frontend-lb" {
  source = "./modules/frontend-lb"

  project_id         = var.project_id
  region             = var.region
  environments       = local.frontend_environments_with_websocket
  base_resource_name = "frontend-v2"
  dns_zone_name      = var.frontend_dns_zone_name
  root_domain        = var.frontend_root_domain
}

module "agent_health_checker" {
  source = "./modules/agent-health-checker"

  project_id              = var.project_id
  region                  = var.region
  vpc_access_connector_id = module.orchestrator.vpc_access_connector_id
}
