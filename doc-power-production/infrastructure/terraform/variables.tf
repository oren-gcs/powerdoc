variable "aws_region" {
  description = "The AWS region to build in."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "The AWS profile to use for authentication."
  type        = string
  default     = "default"
}

variable "project_name" {
  description = "The name of the project."
  type        = string
  default     = "doc-power"
}

variable "environment" {
  description = "The deployment environment."
  type        = string
  default     = "production"
}

variable "cluster_name" {
  description = "The name for the EKS Kubernetes cluster."
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block for the VPC."
  type        = string
}

variable "public_subnets" {
  description = "A list of public subnet CIDR blocks."
  type        = list(string)
}

variable "private_subnets" {
  description = "A list of private subnet CIDR blocks."
  type        = list(string)
}

variable "allowed_ips_for_api" {
  description = "List of CIDR blocks to allow access to the EKS API endpoint."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_instance_type" {
  description = "The EC2 instance type for the EKS worker nodes."
  type        = string
  default     = "t3.medium"
}

variable "node_desired_size" {
  description = "Desired number of worker nodes."
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum number of worker nodes."
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of worker nodes."
  type        = number
  default     = 3
}
