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

resource "google_service_account" "websocket-service-account" {
  account_id  = "websocket-service-account"
  description = "Managed by Terraform - do not edit"
  project     = data.google_project.default.project_id
}

output "websocket-service-account-name" {
  value = google_service_account.websocket-service-account.email
}
