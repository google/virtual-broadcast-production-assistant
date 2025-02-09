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


data "google_project" "default" {}

resource "google_cloudbuild_trigger" "infra" {
  name        = "terraform-infra"
  description = "(Managed by Terraform, do not edit) - Trigger for terraform"
  project     = data.google_project.default.project_id
  location    = "europe-west1"

  github {
    owner = "justingrayston"
    name  = "virtual-production-assistant"
    push {
      branch = "^main$"
    }
  }

  filename        = "build/infrastructure/cloudbuild.yaml"
  service_account = "cloud-build-runner@${data.google_project.default.project_id}.iam.gserviceaccount.com"
}



output "repo_name_used" {
  value = var.cloud-source-repositories-repo-name
}

output "trigger_name" {
  value = google_cloudbuild_trigger.infra.name
}
