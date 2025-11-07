terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {}

module "vpc" {
  source = "./modules/vpc"

  project_name    = var.project_name
  cluster_name    = var.cluster_name
  environment     = var.environment
  vpc_cidr        = var.vpc_cidr
  public_subnets  = var.public_subnets
  private_subnets = var.private_subnets
  azs             = data.aws_availability_zones.available.names
}

module "eks" {
  source = "./modules/eks"

  cluster_name          = var.cluster_name
  project_name          = var.project_name
  environment           = var.environment
  allowed_ips_for_api   = var.allowed_ips_for_api
  
  vpc_id                = module.vpc.vpc_id
  vpc_cidr              = var.vpc_cidr
  public_subnets        = module.vpc.public_subnet_ids
  private_subnets       = module.vpc.private_subnet_ids

  node_instance_type    = var.node_instance_type
  node_desired_size     = var.node_desired_size
  node_min_size         = var.node_min_size
  node_max_size         = var.node_max_size
}

data "aws_eks_cluster" "cluster" {
  name = module.eks.cluster_id
}

data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_id
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.cluster.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.cluster.token
}

resource "kubernetes_config_map" "aws_auth" {
  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }

  data = {
    mapRoles = yamlencode([
      {
        rolearn  = module.eks.node_role_arn
        username = "system:node:{{EC2PrivateDNSName}}"
        groups = [
          "system:bootstrappers",
          "system:nodes"
        ]
      }
    ])
  }

  depends_on = [
    module.eks.node_group_ready
  ]
}
