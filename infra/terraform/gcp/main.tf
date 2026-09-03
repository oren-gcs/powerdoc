terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
}

variable "project" { type = string }
variable "region" { default = "us-central1" }
variable "name" { default = "docflow" }

provider "google" {
  project = var.project
  region  = var.region
}

resource "google_sql_database_instance" "pg" {
  name             = "${var.name}-pg"
  database_version = "POSTGRES_16"
  region           = var.region
  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled = true
    }
  }
}

resource "google_sql_database" "db" {
  name     = "docflow"
  instance = google_sql_database_instance.pg.name
}

resource "google_storage_bucket" "docs" {
  name     = "${var.project}-${var.name}-documents"
  location = var.region
}

resource "google_cloud_run_v2_service" "api" {
  name     = "${var.name}-api"
  location = var.region
  template {
    containers {
      image = "gcr.io/${var.project}/docflow-api:latest"
      ports { container_port = 8000 }
      env {
        name  = "CLOUD_PROVIDER"
        value = "gcp"
      }
      env {
        name  = "DATABASE_URL"
        value = "postgresql+psycopg://docflow:changeme@/${google_sql_database.db.name}?host=/cloudsql/${google_sql_database_instance.pg.connection_name}"
      }
    }
  }
}

resource "google_cloud_run_v2_service" "web" {
  name     = "${var.name}-web"
  location = var.region
  template {
    containers {
      image = "gcr.io/${var.project}/docflow-web:latest"
      ports { container_port = 80 }
    }
  }
}

output "api_uri" { value = google_cloud_run_v2_service.api.uri }
output "web_uri" { value = google_cloud_run_v2_service.web.uri }
output "bucket" { value = google_storage_bucket.docs.name }
