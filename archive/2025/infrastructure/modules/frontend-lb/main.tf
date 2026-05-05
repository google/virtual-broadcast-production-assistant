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
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_compute_global_address" "static_ip" {
  project = var.project_id
  name    = "${var.base_resource_name}-static-ip"
}

resource "google_compute_managed_ssl_certificate" "ssl_certificate" {
  project = var.project_id
  name    = "${var.base_resource_name}-ssl-certificate"
  managed {
    domains = local.all_domains
  }
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_backend_service" "backend_service" {
  for_each  = var.environments
  project   = var.project_id
  name      = "${each.value.service_name}-backend-service"
  protocol  = "HTTP"
  port_name = "http"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.serverless_neg[each.key].id
  }

  connection_draining_timeout_sec = 600
  session_affinity                = "CLIENT_IP"
}

resource "google_compute_backend_service" "orchestrator_backend_service" {
  for_each  = var.environments
  project   = var.project_id
  name      = "orchestrator-agent-backend-service-${each.key}"
  protocol  = "HTTP"
  port_name = "http"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.orchestrator_neg[each.key].id
  }

  connection_draining_timeout_sec = 300
  enable_cdn = false
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
    service = google_cloud_run_v2_service.frontend[each.key].name
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_region_network_endpoint_group" "orchestrator_neg" {
  for_each              = var.environments
  project               = var.project_id
  name                  = "orchestrator-agent-neg-${each.key}"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = "orchestrator-agent-${each.key}"
  }
}

resource "google_compute_url_map" "url_map" {
  project         = var.project_id
  name            = "${var.base_resource_name}-url-map"
  default_service = google_compute_backend_service.backend_service["stable"].id

  host_rule {
    hosts        = [var.environments["staging"].custom_domain]
    path_matcher = "staging-matcher"
  }
  host_rule {
    hosts        = [var.environments["stable"].custom_domain]
    path_matcher = "stable-matcher"
  }

  path_matcher {
    name            = "staging-matcher"
    default_service = google_compute_backend_service.backend_service["staging"].id
    path_rule {
      paths   = ["/ws/*"]
      service = google_compute_backend_service.orchestrator_backend_service["staging"].id
    }
    path_rule {
      paths   = ["/*"]
      service = google_compute_backend_service.backend_service["staging"].id
    }
  }
  path_matcher {
    name            = "stable-matcher"
    default_service = google_compute_backend_service.backend_service["stable"].id
    path_rule {
      paths   = ["/ws/*"]
      service = google_compute_backend_service.orchestrator_backend_service["stable"].id
    }
    path_rule {
      paths   = ["/*"]
      service = google_compute_backend_service.backend_service["stable"].id
    }
  }
}

resource "google_compute_target_https_proxy" "https_proxy" {
  project          = var.project_id
  name             = "${var.base_resource_name}-https-proxy"
  url_map          = google_compute_url_map.url_map.id
  ssl_certificates = [google_compute_managed_ssl_certificate.ssl_certificate.id]
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_global_forwarding_rule" "forwarding_rule" {
  project               = var.project_id
  name                  = "${var.base_resource_name}-forwarding-rule"
  target                = google_compute_target_https_proxy.https_proxy.id
  ip_address            = google_compute_global_address.static_ip.address
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_dns_managed_zone" "dns_zone" {
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

resource "google_cloud_run_v2_service" "frontend" {
  for_each = var.environments
  project  = var.project_id
  name     = each.value.service_name
  location = var.region
  deletion_protection = false

  template {
    containers {
      image = each.value.container_image
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }
    }
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}

resource "google_cloud_run_v2_service_iam_member" "frontend_invoker" {
  for_each = google_cloud_run_v2_service.frontend
  project  = each.value.project
  location = each.value.location
  name     = each.value.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
