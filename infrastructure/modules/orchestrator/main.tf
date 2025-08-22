resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "compute.googleapis.com",
    "dns.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
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

resource "google_compute_backend_service" "agent_engine_backend_service" {
  project = var.project_id
  name    = "${var.service_name}-agent-engine-backend-service"
  protocol = "HTTP"
  port_name = "http"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = var.reverse_proxy_neg_id
  }
}

resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  project               = var.project_id
  name                  = "${var.service_name}-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = google_cloud_run_v2_service.orchestrator_agent.name
  }
}

resource "google_compute_url_map" "url_map" {
  project = var.project_id
  name    = "${var.service_name}-url-map"
  default_service = google_compute_backend_service.backend_service.id

  host_rule {
    hosts        = [var.custom_domain]
    path_matcher = "agent-engine-matcher"
  }

  path_matcher {
    name = "agent-engine-matcher"
    default_service = google_compute_backend_service.backend_service.id

    path_rule {
      paths   = ["/agent-engine/*"]
      service = google_compute_backend_service.agent_engine_backend_service.id
    }
  }
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

resource "google_cloud_run_v2_service" "orchestrator_agent" {
  project  = var.project_id
  name     = var.service_name
  location = var.region

  template {
    containers {
      image = var.container_image
      ports {
        name       = "http1"
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
    service_account     = var.service_account_email
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "ALL_TRAFFIC"
    }
  }

  traffic {
    type     = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent  = 100
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }

  depends_on = [google_vpc_access_connector.connector]
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
  machine_type = "e2-micro"
  min_instances = 2
  max_instances = 3
}

resource "google_compute_router" "router" {
  project = var.project_id
  name    = "${var.service_name}-router"
  region  = var.region
  network = google_compute_network.vpc_network.id
}

resource "google_compute_address" "nat_ip" {
  project = var.project_id
  name    = "${var.service_name}-nat-ip"
  region  = var.region
}

resource "google_compute_router_nat" "nat" {
  project                            = var.project_id
  name                               = "${var.service_name}-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  subnetwork {
    name                     = google_compute_subnetwork.vpc_subnetwork.id
    source_ip_ranges_to_nat  = ["ALL_IP_RANGES"]
  }
  nat_ip_allocate_option             = "MANUAL_ONLY"
  nat_ips                            = [google_compute_address.nat_ip.self_link]
}
