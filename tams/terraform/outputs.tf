output "cloud_run_url" {
  value = google_cloud_run_service.tams_api.status[0].url
}

output "build_command" {
  value = "./build_and_push.sh"
  description = "Run this script from the root of the repository to build and push the real image."
}

output "curl_test_command" {
  value = "curl -H \"Authorization: Bearer $(gcloud auth print-identity-token)\" ${google_cloud_run_service.tams_api.status[0].url}/service"
  description = "Run this command to test the API after deploying the real image."
}
