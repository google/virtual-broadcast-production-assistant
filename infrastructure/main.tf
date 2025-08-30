provider "google" {
  project = var.project_id
  region  = var.region
}

module "orchestrator" {
  source = "./modules/orchestrator"

  project_id            = var.project_id
  region                = var.region
  environments          = var.orchestrator_environments
  dns_zone_name         = var.dns_zone_name
  root_domain           = var.root_domain
  service_account_email = var.orchestrator_service_account_email
}

module "frontend_stable" {
  source = "./modules/frontend"

  project_id      = var.project_id
  region          = var.region
  service_name    = "frontend-v2-stable"
  container_image = var.frontend_container_image_stable
}

module "frontend_staging" {
  source = "./modules/frontend"

  project_id      = var.project_id
  region          = var.region
  service_name    = "frontend-v2-staging"
  container_image = var.frontend_container_image_staging
}

module "agent_health_checker" {
  source = "./modules/agent-health-checker"

  project_id              = var.project_id
  region                  = var.region
  vpc_access_connector_id = module.orchestrator.vpc_access_connector_id
}

module "activity_agent" {
  source = "./modules/activity-agent"

  project_id   = var.project_id
  service_name = var.activity_agent_service_name
}
