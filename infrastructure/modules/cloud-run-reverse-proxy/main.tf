
resource "google_cloud_run_v2_service" "reverse_proxy" {
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
      env {
        name  = "AGENT_ENGINE_URL"
        value = var.agent_engine_url
      }
    }
    scaling {
      min_instance_count = 1
      max_instance_count = 10
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

resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  project               = var.project_id
  name                  = "${var.service_name}-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = google_cloud_run_v2_service.reverse_proxy.name
  }
}

resource "google_compute_network" "vpc_network" {
  project                 = var.project_id
  name                    = var.vpc_network_name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "vpc_subnetwork" {
  project       = var.project_id
  name          = var.vpc_subnet_name
  ip_cidr_range = "10.10.30.0/28"
  region        = var.region
  network       = google_compute_network.vpc_network.id
}

resource "google_vpc_access_connector" "connector" {
  project       = var.project_id
  name          = "${var.service_name}-vpc-conn"
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
