terraform {
  backend "gcs" {
    bucket  = "ibc-smart-stories-tams-state" # Update this to your newly created GCS state bucket name if different
    prefix  = "terraform/state"
  }
}
