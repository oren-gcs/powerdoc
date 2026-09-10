terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
}

variable "project" { type = string }
variable "region" { default = "us-central1" }
variable "name" { default = "docflow" }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "database_url" {
  type      = string
  sensitive = true
  description = "Full SQLAlchemy URL pointing at Cloud SQL"
}

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

resource "google_sql_user" "docflow" {
  name     = "docflow"
  instance = google_sql_database_instance.pg.name
  password = var.db_password
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
      image = "gcr.io/${var.project}/docflow-api:2.0.0"
      ports { container_port = 8000 }
      env {
        name  = "CLOUD_PROVIDER"
        value = "gcp"
      }
      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }
    }
  }
}

resource "google_cloud_run_v2_service" "web" {
  name     = "${var.name}-web"
  location = var.region
  template {
    containers {
      image = "gcr.io/${var.project}/docflow-web:2.0.0"
      ports { container_port = 80 }
    }
  }
}

output "api_uri" { value = google_cloud_run_v2_service.api.uri }
output "web_uri" { value = google_cloud_run_v2_service.web.uri }
output "bucket" { value = google_storage_bucket.docs.name }
output "sql_connection" { value = google_sql_database_instance.pg.connection_name }
