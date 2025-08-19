module "orchestrator" {
  source = "./modules/orchestrator"

  project_id    = var.project_id
  region        = var.region
  service_name  = var.orchestrator_service_name
  custom_domain = var.orchestrator_custom_domain
  dns_zone_name = var.dns_zone_name
  root_domain           = var.root_domain
  container_image       = var.orchestrator_container_image
  service_account_email = var.orchestrator_service_account_email
}


module "activity_agent" {
  source = "./modules/activity-agent"

  project_id   = var.project_id
  service_name = var.activity_agent_service_name
}

module "agent_health_checker" {
  source = "./modules/agent-health-checker"

  project_id                         = var.project_id
  region                             = var.region
  cloud_run_job_service_account_email = var.orchestrator_service_account_email # Reusing the orchestrator service account for simplicity

}
