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


/* This file sets up the Cloud Run instace for the initial deployment
of the websocket server */


resource "google_cloud_run_v2_service" "websocket-server" {
  name     = "websocket-server"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    labels = {
      managed-by = "terraform"
    }
    service_account  = var.service_account
    session_affinity = true

    containers {
      ports {
        container_port = 8081
      }
      image = var.container_image
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

    }

    scaling {
      max_instance_count = 1
    }

  }



  # Terraform, please don't worry if we deploy a new version
  lifecycle {
    ignore_changes = all
  }

}


resource "google_cloud_run_v2_service_iam_member" "websocket-server" {
  name   = google_cloud_run_v2_service.websocket-server.name
  role   = "roles/run.invoker"
  member = "allUsers"
}
