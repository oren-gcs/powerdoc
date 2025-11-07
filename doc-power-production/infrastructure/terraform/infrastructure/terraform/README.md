# Doc Power - Terraform Infrastructure

## Quick Start

```bash
cd infrastructure/terraform
terraform init -reconfigure
terraform plan -var-file="prod.tfvars"
terraform apply -var-file="prod.tfvars"
```

## Access Cluster

```bash
aws eks update-kubeconfig --name doc-power-prod-cluster --region us-east-1
kubectl get nodes
```

## Cleanup

```bash
terraform destroy -var-file="prod.tfvars" -auto-approve
```
