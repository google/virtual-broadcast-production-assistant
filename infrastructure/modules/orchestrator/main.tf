terraform {
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "3.6.0"
    }
  }
}

locals {
  # Create a filtered map of environments that have a custom_domain defined.
  domain_environments = {
    for key, env in var.environments : key => env if try(env.custom_domain, null) != null
  }
  # Create a list of all custom domains.
  all_domains = [for env in var.environments : env.custom_domain if try(env.custom_domain, null) != null]
}

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "compute.googleapis.com",
    "dns.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
    "clouddeploy.googleapis.com",
    "aiplatform.googleapis.com",
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_compute_global_address" "static_ip" {
  project = var.project_id
  name    = "orchestrator-static-ip"
}

resource "google_compute_managed_ssl_certificate" "ssl_certificate" {
  project = var.project_id
  name    = "orchestrator-ssl-certificate"
  managed {
    domains = local.all_domains
  }
}

resource "google_compute_backend_service" "backend_service" {
  project   = var.project_id
  name      = "orchestrator-backend-service"
  protocol  = "HTTP"
  port_name = "http"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  dynamic "backend" {
    for_each = google_compute_region_network_endpoint_group.serverless_neg
    content {
      group = backend.value.id
    }
  }

  connection_draining_timeout_sec = 600
  session_affinity                = "CLIENT_IP"
}

resource "random_id" "neg_suffix" {
  for_each = var.environments
  byte_length = 4
  keepers = {
    service = each.value.service_name
  }
}

resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  for_each              = var.environments
  project               = var.project_id
  name                  = "${each.value.service_name}-neg-${random_id.neg_suffix[each.key].hex}"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = google_cloud_run_v2_service.orchestrator_agent[each.key].name
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_url_map" "url_map" {
  project         = var.project_id
  name            = "orchestrator-url-map"
  default_service = google_compute_backend_service.backend_service.id
}

resource "google_compute_target_https_proxy" "https_proxy" {
  project          = var.project_id
  name             = "orchestrator-https-proxy"
  url_map          = google_compute_url_map.url_map.id
  ssl_certificates = [google_compute_managed_ssl_certificate.ssl_certificate.id]
}

resource "google_compute_global_forwarding_rule" "forwarding_rule" {
  project               = var.project_id
  name                  = "orchestrator-forwarding-rule"
  target                = google_compute_target_https_proxy.https_proxy.id
  ip_address            = google_compute_global_address.static_ip.address
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

resource "google_dns_managed_zone" "dns_zone" {
  # Create DNS zone only if a root domain is provided
  count         = var.root_domain != "" ? 1 : 0
  project       = var.project_id
  name          = var.dns_zone_name
  dns_name      = "${var.root_domain}."
  description   = "Managed zone for ${var.root_domain}"
  force_destroy = true
}

resource "google_dns_record_set" "dns_records" {
  for_each = local.domain_environments

  project      = var.project_id
  name         = "${each.value.custom_domain}."
  type         = "A"
  ttl          = 300
  managed_zone = google_dns_managed_zone.dns_zone[0].name
  rrdatas      = [google_compute_global_address.static_ip.address]
  depends_on   = [google_dns_managed_zone.dns_zone]
}

resource "google_cloud_run_v2_service" "orchestrator_agent" {
  for_each = var.environments
  project  = var.project_id
  name     = each.value.service_name
  location = var.region

  template {
    containers {
      image = each.value.container_image
      ports {
        name           = "http1"
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }
    }
    scaling {
      min_instance_count = 1
      max_instance_count = 100
    }
    session_affinity    = true
    timeout             = "3600s"
    service_account     = var.service_account_email
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "ALL_TRAFFIC"
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }

  depends_on = [google_vpc_access_connector.connector]
}

resource "google_cloud_run_v2_service_iam_member" "orchestrator_agent_invoker" {
  for_each = google_cloud_run_v2_service.orchestrator_agent
  project  = each.value.project
  location = each.value.location
  name     = each.value.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_compute_network" "vpc_network" {
  project                 = var.project_id
  name                    = var.vpc_network_name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "vpc_subnetwork" {
  project       = var.project_id
  name          = var.vpc_subnet_name
  ip_cidr_range = "10.10.10.0/28"
  region        = var.region
  network       = google_compute_network.vpc_network.id
}

resource "google_vpc_access_connector" "connector" {
  project       = var.project_id
  name          = "orchestrator-vpc-conn"
  region        = var.region
  subnet {
    name = google_compute_subnetwork.vpc_subnetwork.name
  }
  machine_type  = "e2-micro"
  min_instances = 2
  max_instances = 3
}

resource "google_compute_router" "router" {
  project = var.project_id
  name    = "orchestrator-router"
  region  = var.region
  network = google_compute_network.vpc_network.id
}

resource "google_compute_address" "nat_ip" {
  project = var.project_id
  name    = "orchestrator-nat-ip"
  region  = var.region
}

resource "google_compute_router_nat" "nat" {
  project                            = var.project_id
  name                               = "orchestrator-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  subnetwork {
    name                    = google_compute_subnetwork.vpc_subnetwork.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
  nat_ip_allocate_option = "MANUAL_ONLY"
  nat_ips                = [google_compute_address.nat_ip.self_link]
}

# Note on Egress/Ingress IP:
# All Cloud Run services in this module use the same VPC connector, which routes
# outbound traffic through a single Cloud NAT (orchestrator-nat). This NAT has a
# single static IP address (orchestrator-nat-ip), providing a consistent
# egress IP for all environments.
# For ingress, all services are attached as backends to a single load balancer
# via NEGs. This load balancer has a single static global IP address, providing
# a consistent ingress IP for external services to whitelist.

resource "google_clouddeploy_target" "targets" {
  for_each = var.environments
  project  = var.project_id
  location = var.region
  name     = "${each.value.service_name}-target"

  run {
    location = "projects/${var.project_id}/locations/${var.region}"
  }

  execution_configs {
    usages          = ["RENDER", "DEPLOY"]
    service_account = var.service_account_email # Use the orchestrator service account
  }
}

resource "google_clouddeploy_delivery_pipeline" "pipeline" {
  project  = var.project_id
  location = var.region
  name     = "orchestrator-agent-delivery"

  serial_pipeline {
    stages {
      target_id = google_clouddeploy_target.targets["staging"].name
      profiles  = []
    }
    stages {
      target_id = google_clouddeploy_target.targets["stable"].name
      profiles  = []
    }
  }

  depends_on = [google_clouddeploy_target.targets]
}
