terraform {
  required_version = ">= 1.5.0"
}

variable "slug" {
  type        = string
  description = "Tenant slug (DNS-safe)"
}

variable "profile" {
  type        = string
  description = "S | M | L compute profile"
  default     = "S"
}

variable "cloud" {
  type        = string
  description = "aws | gcp | local"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "create_dedicated_cluster" {
  type        = bool
  description = "If false: expect shared cluster + dedicated namespace/DB only"
  default     = false
}

locals {
  profile = upper(var.profile)
  db_class = {
    S = { aws = "db.t4g.micro", gcp = "db-f1-micro", storage_gb = 20 }
    M = { aws = "db.t4g.small", gcp = "db-custom-2-7680", storage_gb = 100 }
    L = { aws = "db.r6g.large", gcp = "db-custom-4-16384", storage_gb = 500 }
  }[local.profile]
  name = "docflow-${var.slug}"
}

output "cell_name" { value = local.name }
output "profile" { value = local.profile }
output "db_class" { value = local.db_class }
output "namespace" { value = "tenant-${var.slug}" }
output "create_dedicated_cluster" { value = var.create_dedicated_cluster }

# Wire cloud-specific resources in ../aws-cell and ../gcp-cell callers.
# This module defines the sizing contract every tenant cell must honor.
