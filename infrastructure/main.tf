module "orchestrator" {
  source = "./modules/orchestrator"

  project_id            = var.project_id
  region                = var.region
  service_name          = var.orchestrator_service_name
  custom_domain         = var.orchestrator_custom_domain
  dns_zone_name         = var.dns_zone_name
  root_domain           = var.root_domain
  container_image       = var.orchestrator_container_image
  service_account_email = var.orchestrator_service_account_email
  
  reverse_proxy_neg_id  = module.cloud_run_reverse_proxy.reverse_proxy_neg_id
}


module "agent_health_checker" {
  source = "./modules/agent-health-checker"

  project_id                          = var.project_id
  region                              = var.region
}

module "activity_agent" {
  source = "./modules/activity-agent"

  project_id   = var.project_id
  service_name = var.activity_agent_service_name
}

module "agent_engine" {
  source = "./modules/agent-engine"

  project_id                   = var.project_id
  region                       = var.region
  agent_engine_service_name    = var.agent_engine_service_name
  vpc_network_name             = var.agent_engine_vpc_network_name
  vpc_subnet_name              = var.agent_engine_vpc_subnet_name
  agent_engine_url_secret_name = var.agent_engine_url_secret_name
}

module "cloud_run_reverse_proxy" {
  source = "./modules/cloud-run-reverse-proxy"

  project_id                = var.project_id
  region                    = var.region
  service_name              = var.reverse_proxy_service_name
  container_image           = var.reverse_proxy_container_image
  service_account_email     = var.orchestrator_service_account_email
  vpc_network_name          = "${var.reverse_proxy_service_name}-vpc"
  vpc_subnet_name           = "${var.reverse_proxy_service_name}-subnet"
  agent_engine_url          = var.agent_engine_url
}
