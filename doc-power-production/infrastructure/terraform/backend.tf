terraform {
  backend "s3" {
    bucket  = "doc-power-tf-state"
    key     = "doc-power/prod/terraform.tfstate"
    region  = "us-east-1"
    profile = "terraform-role"
  }
}
