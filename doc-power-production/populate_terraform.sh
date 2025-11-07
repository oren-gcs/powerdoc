#!/bin/bash
#
# CORRECTED Terraform Setup Script - WORKING VERSION
# Fixes: main.tf module declarations, proper HCL syntax
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

TF_DIR="infrastructure/terraform"
VPC_MODULE_DIR="${TF_DIR}/modules/vpc"
EKS_MODULE_DIR="${TF_DIR}/modules/eks"

echo "=========================================="
echo "Terraform Setup (FINAL FIX)"
echo "=========================================="
echo ""

read -p "Enter AWS profile name [terraform-role]: " INPUT_PROFILE
AWS_PROFILE_NAME="${INPUT_PROFILE:-terraform-role}"
echo -e "${GREEN}✅ AWS Profile: ${AWS_PROFILE_NAME}${NC}"

read -p "Enter AWS region [us-east-1]: " INPUT_REGION
AWS_REGION="${INPUT_REGION:-us-east-1}"
echo -e "${GREEN}✅ AWS Region: ${AWS_REGION}${NC}"

read -p "Enter S3 bucket name [doc-power-tf-state]: " INPUT_BUCKET
STATE_BUCKET="${INPUT_BUCKET:-doc-power-tf-state}"
echo -e "${GREEN}✅ S3 Bucket: ${STATE_BUCKET}${NC}"

echo ""
mkdir -p ${TF_DIR} ${VPC_MODULE_DIR} ${EKS_MODULE_DIR}

# DELETE OLD FILES
rm -f ${TF_DIR}/main.tf ${EKS_MODULE_DIR}/main.tf ${EKS_MODULE_DIR}/outputs.tf

# ================================================================
# 1. BACKEND.TF
# ================================================================
cat > ${TF_DIR}/backend.tf << EOF
terraform {
  backend "s3" {
    bucket  = "${STATE_BUCKET}"
    key     = "doc-power/prod/terraform.tfstate"
    region  = "${AWS_REGION}"
    profile = "${AWS_PROFILE_NAME}"
  }
}
EOF
echo "✅ backend.tf"

# ================================================================
# 2. VARIABLES.TF (ROOT)
# ================================================================
cat > ${TF_DIR}/variables.tf << 'VARIABLES_EOF'
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
VARIABLES_EOF
echo "✅ variables.tf"

# ================================================================
# 3. PROD.TFVARS
# ================================================================
cat > ${TF_DIR}/prod.tfvars << EOF
aws_region           = "${AWS_REGION}"
aws_profile          = "${AWS_PROFILE_NAME}"
project_name         = "doc-power"
environment          = "production"
cluster_name         = "doc-power-prod-cluster"
vpc_cidr             = "10.0.0.0/16"
public_subnets       = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnets      = ["10.0.10.0/24", "10.0.11.0/24"]
allowed_ips_for_api  = ["0.0.0.0/0"]
node_instance_type   = "t3.medium"
node_desired_size    = 2
node_min_size        = 1
node_max_size        = 3
EOF
echo "✅ prod.tfvars"

# ================================================================
# 4. MAIN.TF (ROOT) - WITH PROPER MODULE DECLARATIONS
# ================================================================
cat > ${TF_DIR}/main.tf << 'MAIN_EOF'
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
  name       = module.eks.cluster_id
  depends_on = [module.eks.node_group_ready]
}

data "aws_eks_cluster_auth" "cluster" {
  name       = module.eks.cluster_id
  depends_on = [module.eks.node_group_ready]
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.cluster.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.cluster.token
}
MAIN_EOF
echo "✅ main.tf (WITH MODULE DECLARATIONS)"

# ================================================================
# 5. OUTPUTS.TF (ROOT)
# ================================================================
cat > ${TF_DIR}/outputs.tf << 'OUTPUTS_EOF'
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnet_ids" {
  value = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "nat_gateway_ips" {
  value = module.vpc.nat_gateway_ips
}

output "eks_cluster_id" {
  value = module.eks.cluster_id
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "kubeconfig_cmd" {
  value = "aws eks update-kubeconfig --name ${module.eks.cluster_id} --region us-east-1 --profile terraform-role"
}
OUTPUTS_EOF
echo "✅ outputs.tf"

# ================================================================
# 6. VPC MODULE - MAIN.TF
# ================================================================
cat > ${VPC_MODULE_DIR}/main.tf << 'VPC_EOF'
variable "project_name" {
  type    = string
  default = "doc-power"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "cluster_name" {
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

variable "azs" {
  type = list(string)
}

locals {
  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = merge(local.tags, {
    Name = "${var.project_name}-vpc"
  })
}

resource "aws_subnet" "public" {
  count                   = length(var.public_subnets)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnets[count.index]
  availability_zone       = var.azs[count.index % length(var.azs)]
  map_public_ip_on_launch = true
  tags = merge(local.tags, {
    Name                               = "${var.project_name}-public-subnet-${count.index + 1}"
    "kubernetes.io/role/elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  })
}

resource "aws_subnet" "private" {
  count             = length(var.private_subnets)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnets[count.index]
  availability_zone = var.azs[count.index % length(var.azs)]
  tags = merge(local.tags, {
    Name                                = "${var.project_name}-private-subnet-${count.index + 1}"
    "kubernetes.io/role/internal-elb"   = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  })
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
  tags = merge(local.tags, {
    Name = "${var.project_name}-igw"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
  tags = merge(local.tags, {
    Name = "${var.project_name}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  count  = length(var.public_subnets)
  domain = "vpc"
  tags = merge(local.tags, {
    Name = "${var.project_name}-nat-eip-${count.index + 1}"
  })
  depends_on = [aws_internet_gateway.gw]
}

resource "aws_nat_gateway" "nat" {
  count         = length(var.public_subnets)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags = merge(local.tags, {
    Name = "${var.project_name}-nat-gw-${count.index + 1}"
  })
  depends_on = [aws_internet_gateway.gw]
}

resource "aws_route_table" "private" {
  count  = length(var.private_subnets)
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat[count.index].id
  }
  tags = merge(local.tags, {
    Name = "${var.project_name}-private-rt-${count.index + 1}"
  })
}

resource "aws_route_table_association" "private" {
  count          = length(var.private_subnets)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
VPC_EOF
echo "✅ vpc/main.tf"

# ================================================================
# 7. VPC MODULE - OUTPUTS.TF
# ================================================================
cat > ${VPC_MODULE_DIR}/outputs.tf << 'VPC_OUT_EOF'
output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = [for s in aws_subnet.public : s.id]
}

output "private_subnet_ids" {
  value = [for s in aws_subnet.private : s.id]
}

output "nat_gateway_ips" {
  value = [for e in aws_eip.nat : e.public_ip]
}
VPC_OUT_EOF
echo "✅ vpc/outputs.tf"

# ================================================================
# 8. EKS MODULE - VARIABLES.TF
# ================================================================
cat > ${EKS_MODULE_DIR}/variables.tf << 'EKS_VAR_EOF'
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
EKS_VAR_EOF
echo "✅ eks/variables.tf"

# ================================================================
# 9. EKS MODULE - MAIN.TF (COMPLETE)
# ================================================================
cat > ${EKS_MODULE_DIR}/main.tf << 'EKS_MAIN_EOF'
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Cluster IAM Role
data "aws_iam_policy_document" "eks_cluster_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eks_cluster" {
  name               = "${var.cluster_name}-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.eks_cluster_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role_policy_attachment" "eks_vpc_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_cluster.name
}

# Cluster Security Group
resource "aws_security_group" "eks_cluster" {
  name        = "${var.cluster_name}-cluster-sg"
  description = "EKS cluster control plane security group"
  vpc_id      = var.vpc_id
  tags        = merge(local.tags, { Name = "${var.cluster_name}-cluster-sg" })

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Node Security Group
resource "aws_security_group" "eks_nodes" {
  name        = "${var.cluster_name}-nodes-sg"
  description = "EKS worker nodes security group"
  vpc_id      = var.vpc_id
  tags        = merge(local.tags, { Name = "${var.cluster_name}-nodes-sg" })

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
  }

  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_cluster.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.30"

  vpc_config {
    subnet_ids              = concat(var.public_subnets, var.private_subnets)
    security_group_ids      = [aws_security_group.eks_cluster.id]
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.allowed_ips_for_api
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  tags                      = local.tags

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_cni_policy,
  ]
}

# OIDC Provider
data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  tags            = local.tags
}

# Node IAM Role
data "aws_iam_policy_document" "eks_nodes_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eks_nodes" {
  name               = "${var.cluster_name}-node-role"
  assume_role_policy = data.aws_iam_policy_document.eks_nodes_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "eks_nodes_worker_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_nodes_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_nodes_ecr_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_instance_profile" "eks_nodes" {
  name = "${var.cluster_name}-node-profile"
  role = aws_iam_role.eks_nodes.name
}

# Node Group
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-nodes"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = var.private_subnets
  version         = aws_eks_cluster.main.version

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  instance_types = [var.node_instance_type]
  ami_type       = "AL2023_x86_64_STANDARD"
  capacity_type  = "ON_DEMAND"
  disk_size      = 20

  tags = merge(local.tags, { Name = "${var.cluster_name}-worker-node" })

  depends_on = [
    aws_iam_role_policy_attachment.eks_nodes_worker_policy,
    aws_iam_role_policy_attachment.eks_nodes_cni_policy,
    aws_iam_role_policy_attachment.eks_nodes_ecr_policy,
  ]

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [scaling_config[0].desired_size]
  }
}

# Add-ons
resource "aws_eks_addon" "vpc_cni" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "vpc-cni"
  addon_version            = "v1.18.0-eksbuild.1"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  service_account_role_arn = aws_iam_role.vpc_cni.arn
  tags                     = local.tags
  depends_on               = [aws_eks_node_group.main]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name               = aws_eks_cluster.main.name
  addon_name                 = "kube-proxy"
  addon_version              = "v1.30.0-eksbuild.3"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  tags                       = local.tags
  depends_on                 = [aws_eks_node_group.main]
}

resource "aws_eks_addon" "coredns" {
  cluster_name               = aws_eks_cluster.main.name
  addon_name                 = "coredns"
  addon_version              = "v1.10.1-eksbuild.11"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  tags                       = local.tags
  depends_on                 = [aws_eks_node_group.main]
}

resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = "v1.28.0-eksbuild.1"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"
  service_account_role_arn    = aws_iam_role.ebs_csi_driver.arn
  tags                        = local.tags
  depends_on                  = [aws_eks_node_group.main]
}

# IRSA - VPC CNI
data "aws_iam_policy_document" "vpc_cni_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:aws-node"]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "vpc_cni" {
  name               = "${var.cluster_name}-vpc-cni"
  assume_role_policy = data.aws_iam_policy_document.vpc_cni_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "vpc_cni" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.vpc_cni.name
}

# IRSA - EBS CSI
data "aws_iam_policy_document" "ebs_csi_driver_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:ebs-csi-controller-sa"]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ebs_csi_driver" {
  name               = "${var.cluster_name}-ebs-csi-driver"
  assume_role_policy = data.aws_iam_policy_document.ebs_csi_driver_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "ebs_csi_driver" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
  role       = aws_iam_role.ebs_csi_driver.name
}
EKS_MAIN_EOF
echo "✅ eks/main.tf"

# ================================================================
# 10. EKS MODULE - OUTPUTS.TF
# ================================================================
cat > ${EKS_MODULE_DIR}/outputs.tf << 'EKS_OUT_EOF'
output "cluster_id" {
  value = aws_eks_cluster.main.id
}

output "node_group_ready" {
  value      = aws_eks_node_group.main.id
  depends_on = [aws_eks_node_group.main]
}

output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "cluster_ca_certificate" {
  value     = aws_eks_cluster.main.certificate_authority[0].data
  sensitive = true
}

output "cluster_version" {
  value = aws_eks_cluster.main.version
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.eks.arn
}

output "node_role_arn" {
  value = aws_iam_role.eks_nodes.arn
}

output "node_security_group_id" {
  value = aws_security_group.eks_nodes.id
}
EKS_OUT_EOF
echo "✅ eks/outputs.tf"

# ================================================================
# 11. .GITIGNORE
# ================================================================
cat > ${TF_DIR}/.gitignore << 'GIT_EOF'
*.tfstate
*.tfstate.*
.terraform/
.terraform.lock.hcl
terraform.tfvars
.vscode/
*.swp
*.log
GIT_EOF
echo "✅ .gitignore"

# ================================================================
# 12. README.MD
# ================================================================
cat > ${TF_DIR}/README.md << 'README_EOF'
# Doc Power - Terraform Infrastructure

## Quick Start

```bash
cd infrastructure/terraform
terraform init -reconfigure
terraform validate
terraform plan -var-file="prod.tfvars"
terraform apply -var-file="prod.tfvars"
```

## Access Cluster

```bash
aws eks update-kubeconfig --name doc-power-prod-cluster --region us-east-1 --profile terraform-role
kubectl get nodes
```

## Cleanup

```bash
terraform destroy -var-file="prod.tfvars" -auto-approve
```
README_EOF
echo "✅ README.md"

echo ""
echo "=========================================="
echo "✅ ALL FILES CREATED SUCCESSFULLY"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "  1. cd infrastructure/terraform"
echo "  2. terraform init -reconfigure"
echo "  3. terraform validate"
echo "  4. terraform plan -var-file=\"prod.tfvars\""
echo "  5. terraform apply -var-file=\"prod.tfvars\""
echo ""
echo "=========================================="