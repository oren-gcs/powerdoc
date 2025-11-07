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
