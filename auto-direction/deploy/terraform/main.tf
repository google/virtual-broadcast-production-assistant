terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.50.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "vpcaccess.googleapis.com",
    "compute.googleapis.com",
    "aiplatform.googleapis.com"
  ])
  service            = each.key
  disable_on_destroy = false
}

# 2. Custom Private VPC Network
resource "google_compute_network" "custom_vpc" {
  name                    = "broadcast-custom-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "subnet" {
  name          = "broadcast-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.custom_vpc.id
}

# 3. Serverless VPC Access Connector
resource "google_vpc_access_connector" "vpc_connector" {
  name          = "vpc-con"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.custom_vpc.name
  depends_on    = [google_project_service.apis]
}

# 4. Identity & Access Management (Service Account)
resource "google_service_account" "sa" {
  account_id   = "decoupled-broadcast-sa"
  display_name = "Decoupled Broadcast Service Account"
}

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.sa.email}"
}

# 5. Cloud Run: Cuez Automator (INTERNAL ONLY)
resource "google_cloud_run_v2_service" "cuez_bridge" {
  name     = "cuez-bridge"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.sa.email
    containers {
      image   = var.container_image_url
      command = ["python", "src/cuez_bridge.py"]
      ports { container_port = 8080 }
    }
  }
}

# 6. Cloud Run: Shure WebMCP (INTERNAL ONLY)
resource "google_cloud_run_v2_service" "shure_bridge" {
  name     = "shure-bridge"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.sa.email
    containers {
      image   = var.container_image_url
      command = ["python", "src/shure_bridge.py"]
      ports { container_port = 8080 }
    }
  }
}

# 7. Cloud Run: Director WebSocket Proxy (PUBLIC)
resource "google_cloud_run_v2_service" "director_proxy" {
  name     = "director-proxy"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account  = google_service_account.sa.email
    session_affinity = true # Match WebSocket session states

    containers {
      image   = var.container_image_url
      command = ["python", "src/director_proxy.py"]
      ports { container_port = 8080 }

      env {
        name  = "CUEZ_API_URL"
        value = google_cloud_run_v2_service.cuez_bridge.uri
      }
      env {
        name  = "SHURE_API_URL"
        value = google_cloud_run_v2_service.shure_bridge.uri
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.vpc_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }
}

# 8. Cloud Run: FOH WebSocket Proxy & Frontend (PUBLIC)
resource "google_cloud_run_v2_service" "foh_proxy" {
  name     = "foh-proxy"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account  = google_service_account.sa.email
    session_affinity = true

    containers {
      image   = var.container_image_url
      command = ["python", "src/foh_proxy.py"]
      ports { container_port = 8080 }

      env {
        name  = "CUEZ_API_URL"
        value = google_cloud_run_v2_service.cuez_bridge.uri
      }
      env {
        name  = "SHURE_API_URL"
        value = google_cloud_run_v2_service.shure_bridge.uri
      }
      env {
        name  = "DIRECTOR_API_URL"
        value = google_cloud_run_v2_service.director_proxy.uri
      }
      env {
        name  = "DIRECTOR_PUBLIC_URL"
        value = google_cloud_run_v2_service.director_proxy.uri
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.vpc_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }
}

# 9. IAM Open Policies for Public Services
resource "google_cloud_run_v2_service_iam_member" "foh_public" {
  name     = google_cloud_run_v2_service.foh_proxy.name
  location = google_cloud_run_v2_service.foh_proxy.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "director_public" {
  name     = google_cloud_run_v2_service.director_proxy.name
  location = google_cloud_run_v2_service.director_proxy.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
