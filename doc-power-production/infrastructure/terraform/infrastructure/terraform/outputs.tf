output "vpc_id" {
  description = "The ID of the newly created VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "nat_gateway_ips" {
  description = "Elastic IPs of NAT Gateways (one per AZ)"
  value       = module.vpc.nat_gateway_ips
}

output "eks_cluster_id" {
  description = "The name/id of the EKS cluster"
  value       = module.eks.cluster_id
}

output "eks_cluster_endpoint" {
  description = "Endpoint for your EKS Kubernetes API"
  value       = module.eks.cluster_endpoint
}

output "kubeconfig_command" {
  description = "Command to update your local kubeconfig"
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_id} --region ${var.aws_region} --profile ${var.aws_profile}"
}
