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

resource "google_container_cluster" "sofie_cluster" {
  name                     = "sofie-cluster"
  location                 = var.region
  remove_default_node_pool = true
  initial_node_count       = 1 # Required even if removing default pool

  network    = var.vpc_self_link
  subnetwork = var.subnetwork_self_link

  ip_allocation_policy {
    cluster_secondary_range_name  = var.subnetwork_pods_range_name
    services_secondary_range_name = var.subnetwork_services_range_name
  }

  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  # Ensure addons like HttpLoadBalancing (for Ingress) are enabled (default)
  addons_config {
    http_load_balancing {
      disabled = false
    }
    # config_connector_config { # Optional: If using Config Connector
    #   enabled = true
    # }

  }

  release_channel {
    channel = "REGULAR"
  }
}

resource "google_container_node_pool" "sofie_primary_nodes" {
  name       = "primary-node-pool"
  location   = var.region # Or specific zone like "${var.region}-a"
  cluster    = google_container_cluster.sofie_cluster.name
  node_count = 1 # Initial node count, autoscaler will manage

  autoscaling {
    min_node_count = 1
    max_node_count = 3
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = "e2-standard-4" # Adjust based on expected load
    disk_size_gb = 100
    disk_type    = "pd-standard" # Consider pd-ssd for better performance

    # Service account and scopes
    service_account = google_service_account.sofie_gke_node_sa.email
    #oauth_scopes =

    # Network tag for firewall rules
    tags = [var.gke_node_tag]

    # Metadata and labels as needed
    metadata = {
      disable-legacy-endpoints = "true"
    }
    labels = {
      "workload-type" = "sofie-backend"
    }
  }
}

variable "gke_node_tag" {
  description = "Network tag applied to GKE nodes for firewall rules"
  type        = string
  default     = "sofie-gke-node"
}

resource "google_service_account" "sofie_gke_node_sa" {
  project      = var.project
  account_id   = "sofie-gke-node-sa"
  display_name = "Service Account for Sofie GKE Nodes"
  description  = "Used by GKE nodes in the Sofie cluster"
}

# resource "google_iap_brand" "project_brand" {
#   # Assumes iap.googleapis.com is enabled by the root module (apis.tf)
#   support_email     = var.iap_support_email
#   application_title = "Sofie Broadcast Automation"
#   # The 'project' attribute is omitted; the provider will infer it.
# }

# resource "google_iap_client" "sofie_iap_client" {
#   display_name = "Sofie GKE Client"
#   brand        = google_iap_brand.project_brand.name # Uses format projects/<project_number>/brands/<brand_id>
# }

# Firewall rulefor IAP TCP Forwarding

resource "google_compute_firewall" "allow_iap_to_nodes" {
  name      = "allow-iap-tcp-to-sofie-nodes"
  network   = var.vpc_self_link
  direction = "INGRESS"
  priority  = 1000 # Default priority

  allow {
    protocol = "tcp"
    # Ports need to match the service exposure (NodePort range or NEG ports)
    # Example for NodePort range:
    ports = ["30000-32767"]
    # Example if Sofie Core Service uses port 80 via NEG:
    # ports    = ["80"]
  }

  source_ranges = ["35.235.240.0/20"] # IAP TCP Forwarding Range
  target_tags   = [var.gke_node_tag]

  description = "Allow IAP TCP forwarding access to Sofie GKE nodes"
}

# Also ensure health check ranges can reach nodes (GKE usually handles this for Ingress)
resource "google_compute_firewall" "allow_health_checks" {
  name      = "allow-lb-health-checks-sofie"
  network   = var.vpc_self_link
  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    # Ports need to match service exposure/health check config
    # Example for NodePort range:
    ports = ["30000-32767"]
    # Example if Sofie Core Service uses port 80 via NEG:
    # ports = ["80"]
  }

  # Google Cloud health checker ranges
  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]

  target_tags = [var.gke_node_tag]
  description = "Allow LB Health Checks to Sofie GKE nodes"
}
