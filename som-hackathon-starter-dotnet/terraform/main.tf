provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable APIs
resource "google_project_service" "compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "vpcaccess" {
  service            = "vpcaccess.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "managedkafka" {
  service            = "managedkafka.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}


# Networking
resource "google_compute_network" "vpc" {
  name                    = "som-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.compute]
}

resource "google_compute_subnetwork" "subnet" {
  name          = "som-subnet"
  ip_cidr_range = "10.0.0.0/24"
  network       = google_compute_network.vpc.id
  region        = var.region
}

# Serverless VPC Access Connector
resource "google_vpc_access_connector" "connector" {
  name          = "som-vpc-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc.name
  min_instances = 2
  max_instances = 3
  depends_on    = [google_project_service.vpcaccess]
}

# Managed Kafka Cluster
resource "google_managed_kafka_cluster" "kafka" {
  cluster_id = var.cluster_name
  location   = var.region

  capacity_config {
    vcpu_count   = 3
    memory_bytes = 3221225472 # 3 GiB
  }

  gcp_config {
    access_config {
      network_configs {
        subnet = google_compute_subnetwork.subnet.id
      }
    }
  }

  rebalance_config {
    mode = "NO_REBALANCE"
  }

  depends_on = [google_project_service.managedkafka]
}

# Kafka Topics
resource "google_managed_kafka_topic" "story_context" {
  topic_id           = "som.story.context"
  cluster            = google_managed_kafka_cluster.kafka.cluster_id
  location           = var.region
  partition_count    = 3
  replication_factor = 3
}

resource "google_managed_kafka_topic" "skills_staging" {
  topic_id           = "som.skills.staging"
  cluster            = google_managed_kafka_cluster.kafka.cluster_id
  location           = var.region
  partition_count    = 3
  replication_factor = 3
}

resource "google_managed_kafka_topic" "skills_events" {
  topic_id           = "som.skills.events"
  cluster            = google_managed_kafka_cluster.kafka.cluster_id
  location           = var.region
  partition_count    = 3
  replication_factor = 3
}

resource "google_managed_kafka_topic" "skills_rejected" {
  topic_id           = "som.skills.rejected"
  cluster            = google_managed_kafka_cluster.kafka.cluster_id
  location           = var.region
  partition_count    = 3
  replication_factor = 3
}

resource "google_managed_kafka_topic" "skills_runs" {
  topic_id           = "som.skills.runs"
  cluster            = google_managed_kafka_cluster.kafka.cluster_id
  location           = var.region
  partition_count    = 3
  replication_factor = 3
}
# Artifact Registry
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.repository_name
  description   = "Docker repository for SOM Skill Worker"
  format        = "DOCKER"
}
# Service Account for Cloud Build
resource "google_service_account" "cloudbuild_sa" {
  account_id   = "som-cloudbuild-sa"
  display_name = "Cloud Build Service Account for SOM"
}

# IAM role for Artifact Registry Writer
resource "google_project_iam_member" "cloudbuild_repo_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}

# IAM role for Storage Object Viewer on source bucket
resource "google_storage_bucket_iam_member" "cloudbuild_source_reader" {
  bucket = var.cloudbuild_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}

# IAM role for Log Writer for Cloud Build SA
resource "google_project_iam_member" "cloudbuild_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}


# Grant Cloud Build SA permission to deploy to Cloud Run
resource "google_project_iam_member" "cloudbuild_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}

# Grant Cloud Build SA permission to act as the worker SA
resource "google_project_iam_member" "cloudbuild_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloudbuild_sa.email}"
}

# Service Account for Cloud Run Worker
resource "google_service_account" "worker_sa" {
  account_id   = "som-worker-sa"
  display_name = "Runtime Service Account for Cloud Run Worker"
}

# Grant Managed Kafka Client access to the Worker SA
resource "google_project_iam_member" "worker_kafka_client" {
  project = var.project_id
  role    = "roles/managedkafka.client"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}

# Grant Log Writer access to the Worker SA
resource "google_project_iam_member" "worker_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}

# Grant Vertex AI User access to the Worker SA
resource "google_project_iam_member" "worker_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}



# Cloud Run Service
resource "google_cloud_run_v2_service" "app" {
  name     = "som-skill-worker"
  location = var.region
  deletion_protection = false

  template {
    service_account = google_service_account.worker_sa.email

    containers {
      image = var.image_url

      ports {
        container_port = 5050
      }

      env {
        name  = "ASPNETCORE_ENVIRONMENT"
        value = "Production"
      }

      env {
        name  = "Kafka__BootstrapServers"
        value = var.kafka_bootstrap_servers
      }

      # Managed Service for Apache Kafka mandates TLS encryption on all broker listeners.
      # Authentication is enforced via OAUTHBEARER using standard Application Default Credentials.
      env {
        name  = "Kafka__SecurityProtocol"
        value = "SaslSsl"
      }

      env {
        name  = "Kafka__SaslMechanism"
        value = "Plain"
      }

      env {
        name  = "Kafka__SaslUsername"
        value = google_service_account.worker_sa.email
      }

      env {
        name  = "GEMINI_MODEL"
        value = "gemini-3-flash-preview"
      }

      env {
        name  = "LOCATION"
        value = "global"
      }




    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "ALL_TRAFFIC"
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 5
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.run]
}

# TODO(security): Implement Identity-Aware Proxy (IAP) to restrict public access once developer identities are collected.
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
