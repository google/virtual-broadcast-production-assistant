resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "compute.googleapis.com",
    "dns.googleapis.com",
    "servicenetworking.googleapis.com",
  ])
  project = var.project_id
  service = each.key
  disable_on_destroy = false
}

resource "google_compute_global_address" "static_ip" {
  project = var.project_id
  name    = "${var.service_name}-static-ip"
}

resource "google_compute_managed_ssl_certificate" "ssl_certificate" {
  project = var.project_id
  name    = "${var.service_name}-ssl-certificate"
  managed {
    domains = [var.custom_domain]
  }
}

resource "google_compute_backend_service" "backend_service" {
  project = var.project_id
  name    = "${var.service_name}-backend-service"
  protocol = "HTTP"
  port_name = "http"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.serverless_neg.id
  }
}

resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  project               = var.project_id
  name                  = "${var.service_name}-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = data.google_cloud_run_v2_service.orchestrator_agent.name
  }
}

resource "google_compute_url_map" "url_map" {
  project = var.project_id
  name    = "${var.service_name}-url-map"
  default_service = google_compute_backend_service.backend_service.id
}

resource "google_compute_target_https_proxy" "https_proxy" {
  project = var.project_id
  name    = "${var.service_name}-https-proxy"
  url_map = google_compute_url_map.url_map.id
  ssl_certificates = [google_compute_managed_ssl_certificate.ssl_certificate.id]
}

resource "google_compute_global_forwarding_rule" "forwarding_rule" {
  project = var.project_id
  name    = "${var.service_name}-forwarding-rule"
  target  = google_compute_target_https_proxy.https_proxy.id
  ip_address = google_compute_global_address.static_ip.address
  port_range = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

resource "google_dns_managed_zone" "dns_zone" {
  project       = var.project_id
  name          = var.dns_zone_name
  dns_name      = "${var.root_domain}."
  description   = "Managed zone for ${var.root_domain}"
  force_destroy = true
}

resource "google_dns_record_set" "dns_record" {
  project = var.project_id
  name    = "${var.custom_domain}."
  type    = "A"
  ttl     = 300
  managed_zone = google_dns_managed_zone.dns_zone.name
  rrdatas = [google_compute_global_address.static_ip.address]
}

# Assuming the Cloud Run service is already deployed and named 'orchestrator-agent'
data "google_cloud_run_v2_service" "orchestrator_agent" {
  project  = var.project_id
  name     = var.service_name
  location = var.region
}
