/*
 Copyright 2025 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 */

data "google_project" "project" {
}


resource "google_compute_network" "vpc" {
  project                 = var.project
  name                    = var.vpc-name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name                     = var.subnet-name
  project                  = var.project
  ip_cidr_range            = "10.1.2.0/24"
  region                   = var.region
  network                  = google_compute_network.vpc.id
  private_ip_google_access = true
  secondary_ip_range {
    range_name    = "pods-range"
    ip_cidr_range = var.pods_cidr_range
  }
  secondary_ip_range {
    range_name    = "services-range"
    ip_cidr_range = var.services_cidr_range
  }

}


resource "google_compute_router" "router" {
  name    = "vpc-router"
  region  = var.region
  project = var.project
  network = google_compute_network.vpc.id

  bgp {
    asn = 64514
  }
}

resource "google_compute_router_nat" "nat" {
  name                               = "vpc-nat"
  project                            = var.project
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Reserve an IP Range for use with Private Service Access
resource "google_compute_global_address" "google-managed-services-range" {

  project       = var.project
  name          = "psa"
  purpose       = "VPC_PEERING"
  prefix_length = "20"
  ip_version    = "IPV4"
  address_type  = "INTERNAL"
  network       = google_compute_network.vpc.self_link
}

# Setup the Private Service Access network connection
resource "google_service_networking_connection" "private_service_access" {

  network                 = google_compute_network.vpc.self_link
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.google-managed-services-range.name]

}

# Create a VPC Access Connector for Cloud Run so it can connect to the Project's VPC
resource "google_vpc_access_connector" "connector" {
  name          = var.vpc-access-connector-name
  ip_cidr_range = var.vpc-access-connector-cidr-range
  region        = var.region
  network       = var.vpc-name

  depends_on = [google_compute_network.vpc]
}

# Firewall rules

resource "google_compute_firewall" "rdp" {
  name          = "allow-rdp"
  network       = google_compute_network.vpc.self_link
  description   = "allows rdp"
  direction     = "INGRESS"
  priority      = 1000
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["rdp"]

  allow {
    protocol = "tcp"
    ports    = ["3389"]
  }
}

resource "google_compute_firewall" "allow_vpc_to_vm_port_7070" {
  name        = "allow-vpc-to-vm-7070"
  network     = google_compute_network.vpc.self_link
  description = "Allows coms to automator"
  direction   = "INGRESS"
  priority    = 1000
  source_ranges = [
    "10.8.0.0/28",
    "10.1.2.0/24",
  ]
  target_tags = ["cuez"]

  allow {
    protocol = "tcp"
    ports    = ["7070"]
  }
}

resource "google_compute_firewall" "agent_builder_outbound_firewall" {
  name        = "agent-builder-to-psc"
  network     = var.vpc-name
  description = ""

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["35.199.192.0/19"]
}
