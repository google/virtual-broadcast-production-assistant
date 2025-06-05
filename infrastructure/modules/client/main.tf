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

# creates orignal pastra frontend cloud run service

resource "google_cloud_run_v2_service" "client-frontend" {
  name     = "client-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    labels = {
      managed-by = "terraform"
    }

    containers {
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
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image
    ]
  }

}


resource "google_cloud_run_v2_service_iam_member" "client-frontend" {
  name   = google_cloud_run_v2_service.client-frontend.name
  role   = "roles/run.invoker"
  member = "allUsers"
}
