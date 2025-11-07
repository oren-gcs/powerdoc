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
