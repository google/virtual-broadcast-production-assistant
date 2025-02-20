/**
 * Copyright 2023 Google LLC
 */

# Output the cuez-custom-proxy service URI
output "cuez-custom-proxy-service-uri" {
  value = google_cloud_run_v2_service.cuez-custom-proxy-service.uri
}

output "proxy-service-account-email" {
  value = google_service_account.cuez-custom-proxy-service-account.email
}
