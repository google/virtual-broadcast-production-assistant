terraform {
  backend "gcs" {
    bucket  = "ibc-smart-stories-initial-deploy-state"
    prefix  = "terraform/state"
  }
}
