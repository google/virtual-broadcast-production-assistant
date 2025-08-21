resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "compute.googleapis.com",
    "dns.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com"
  ])
  project = var.project_id
  service = each.key
  disable_on_destroy = false
}

data "google_project" "project" {
  project_id = var.project_id
}

resource "google_secret_manager_secret" "agent_engine_url" {
  project   = var.project_id
  secret_id = var.agent_engine_url_secret_name

  replication {
    auto {}
  }
}


resource "google_secret_manager_secret_iam_member" "custom_cloud_build_secret_accessor" {
  project   = google_secret_manager_secret.agent_engine_url.project
  secret_id = google_secret_manager_secret.agent_engine_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_secret_manager_secret_iam_member" "custom_cloud_build_secret_version_adder" {
  project   = google_secret_manager_secret.agent_engine_url.project
  secret_id = google_secret_manager_secret.agent_engine_url.secret_id
  role      = "roles/secretmanager.secretVersionAdder"
  member    = "serviceAccount:${var.cloud_build_runner_service_account_email}"
}

resource "google_compute_network" "vpc_network" {
  project                 = var.project_id
  name                    = var.vpc_network_name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "vpc_subnetwork" {
  project       = var.project_id
  name          = var.vpc_subnet_name
  ip_cidr_range = "10.10.20.0/28"
  region        = var.region
  network       = google_compute_network.vpc_network.id
}

resource "google_vpc_access_connector" "connector" {
  project       = var.project_id
  name          = "${var.agent_engine_service_name}-conn"
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
  name    = "${var.agent_engine_service_name}-router"
  region  = var.region
  network = google_compute_network.vpc_network.id
}

resource "google_compute_address" "nat_ip" {
  project = var.project_id
  name    = "${var.agent_engine_service_name}-nat-ip"
  region  = var.region
}

resource "google_compute_router_nat" "nat" {
  project                            = var.project_id
  name                               = "${var.agent_engine_service_name}-nat"
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
