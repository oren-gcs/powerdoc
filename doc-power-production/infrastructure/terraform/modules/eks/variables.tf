variable "cluster_name" {
  type = string
}

variable "project_name" {
  type    = string
  default = "doc-power"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "vpc_id" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "public_subnets" {
  type = list(string)
}

variable "private_subnets" {
  type = list(string)
}

variable "allowed_ips_for_api" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

variable "node_instance_type" {
  type    = string
  default = "t3.medium"
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 3
}
