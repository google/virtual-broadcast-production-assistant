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
output "gke_cluster_name" {
  description = "The name of the GKE cluster"
  value       = google_container_cluster.sofie_cluster.name
}

output "gke_cluster_location" {
  description = "The location (region/zone) of the GKE cluster"
  value       = google_container_cluster.sofie_cluster.location
}

output "gke_node_pool_tag" {
  description = "The network tag applied to the GKE node pool"
  value       = var.gke_node_tag
}

output "vpc_network_name" {
  description = "The name of the VPC network created"
  value       = var.vpc_name
}

# Add outputs for IAP Client ID and Secret )
output "iap_client_id" {
  description = "IAP Client ID"
  value       = google_iap_client.sofie_iap_client.client_id
}
output "iap_client_secret" {
  description = "IAP Client Secret"
  value       = google_iap_client.sofie_iap_client.secret
  sensitive   = true
}
