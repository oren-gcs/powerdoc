#!/bin/bash
#
# Fix IAM Policy Attachment Issues
# This script updates your EKS module to use aws_iam_role_policy_attachment
# instead of the problematic aws_iam_policy_attachment
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

EKS_MODULE="infrastructure/terraform/modules/eks/main.tf"

echo "=========================================="
echo "Fixing IAM Policy Attachments"
echo "=========================================="
echo ""

# Check if file exists
if [ ! -f "$EKS_MODULE" ]; then
    echo -e "${RED}❌ File not found: $EKS_MODULE${NC}"
    echo "Please run this script from your project root directory."
    exit 1
fi

# Backup the file
echo "Creating backup..."
cp "$EKS_MODULE" "${EKS_MODULE}.backup"
echo -e "${GREEN}✅ Backup created: ${EKS_MODULE}.backup${NC}"

echo ""
echo "Applying fixes..."

# Fix 1: Replace aws_iam_policy_attachment with aws_iam_role_policy_attachment for cluster
sed -i 's/resource "aws_iam_policy_attachment" "eks_cluster_policy"/resource "aws_iam_role_policy_attachment" "eks_cluster_policy"/' "$EKS_MODULE"
sed -i 's/resource "aws_iam_policy_attachment" "eks_vpc_cni_policy"/resource "aws_iam_role_policy_attachment" "eks_vpc_cni_policy"/' "$EKS_MODULE"

# Fix 2: Replace aws_iam_policy_attachment with aws_iam_role_policy_attachment for nodes
sed -i 's/resource "aws_iam_policy_attachment" "eks_nodes_worker_policy"/resource "aws_iam_role_policy_attachment" "eks_nodes_worker_policy"/' "$EKS_MODULE"
sed -i 's/resource "aws_iam_policy_attachment" "eks_nodes_cni_policy"/resource "aws_iam_role_policy_attachment" "eks_nodes_cni_policy"/' "$EKS_MODULE"
sed -i 's/resource "aws_iam_policy_attachment" "eks_nodes_ecr_policy"/resource "aws_iam_role_policy_attachment" "eks_nodes_ecr_policy"/' "$EKS_MODULE"

# Fix 3: Remove 'name' parameter and change 'roles' to 'role' for cluster policies
sed -i '/resource "aws_iam_role_policy_attachment" "eks_cluster_policy"/,/^}/ {
    /name[[:space:]]*=/d
    s/roles[[:space:]]*=[[:space:]]*\[aws_iam_role.eks_cluster.name\]/role       = aws_iam_role.eks_cluster.name/
}' "$EKS_MODULE"

sed -i '/resource "aws_iam_role_policy_attachment" "eks_vpc_cni_policy"/,/^}/ {
    /name[[:space:]]*=/d
    s/roles[[:space:]]*=[[:space:]]*\[aws_iam_role.eks_cluster.name\]/role       = aws_iam_role.eks_cluster.name/
}' "$EKS_MODULE"

# Fix 4: Remove 'name' parameter and change 'roles' to 'role' for node policies
sed -i '/resource "aws_iam_role_policy_attachment" "eks_nodes_worker_policy"/,/^}/ {
    /name[[:space:]]*=/d
    s/roles[[:space:]]*=[[:space:]]*\[aws_iam_role.eks_nodes.name\]/role       = aws_iam_role.eks_nodes.name/
}' "$EKS_MODULE"

sed -i '/resource "aws_iam_role_policy_attachment" "eks_nodes_cni_policy"/,/^}/ {
    /name[[:space:]]*=/d
    s/roles[[:space:]]*=[[:space:]]*\[aws_iam_role.eks_nodes.name\]/role       = aws_iam_role.eks_nodes.name/
}' "$EKS_MODULE"

sed -i '/resource "aws_iam_role_policy_attachment" "eks_nodes_ecr_policy"/,/^}/ {
    /name[[:space:]]*=/d
    s/roles[[:space:]]*=[[:space:]]*\[aws_iam_role.eks_nodes.name\]/role       = aws_iam_role.eks_nodes.name/
}' "$EKS_MODULE"

# Fix 5: Update depends_on references in aws_eks_cluster
sed -i 's/aws_iam_policy_attachment.eks_cluster_policy/aws_iam_role_policy_attachment.eks_cluster_policy/g' "$EKS_MODULE"
sed -i 's/aws_iam_policy_attachment.eks_vpc_cni_policy/aws_iam_role_policy_attachment.eks_vpc_cni_policy/g' "$EKS_MODULE"

# Fix 6: Update depends_on references in aws_eks_node_group
sed -i 's/aws_iam_policy_attachment.eks_nodes_worker_policy/aws_iam_role_policy_attachment.eks_nodes_worker_policy/g' "$EKS_MODULE"
sed -i 's/aws_iam_policy_attachment.eks_nodes_cni_policy/aws_iam_role_policy_attachment.eks_nodes_cni_policy/g' "$EKS_MODULE"
sed -i 's/aws_iam_policy_attachment.eks_nodes_ecr_policy/aws_iam_role_policy_attachment.eks_nodes_ecr_policy/g' "$EKS_MODULE"

echo -e "${GREEN}✅ Fixes applied${NC}"
echo ""

# Verify the changes
echo "Verifying changes..."
if grep -q "aws_iam_policy_attachment" "$EKS_MODULE"; then
    echo -e "${YELLOW}⚠️  Warning: Some aws_iam_policy_attachment references still exist${NC}"
    echo "Remaining instances:"
    grep -n "aws_iam_policy_attachment" "$EKS_MODULE"
else
    echo -e "${GREEN}✅ All aws_iam_policy_attachment references updated${NC}"
fi

echo ""
echo "=========================================="
echo "Fix Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review the changes: diff ${EKS_MODULE}.backup ${EKS_MODULE}"
echo "  2. cd infrastructure/terraform"
echo "  3. Remove the problematic resources from state:"
echo "     terraform state rm module.eks.aws_iam_policy_attachment.eks_cluster_policy"
echo "     terraform state rm module.eks.aws_iam_policy_attachment.eks_vpc_cni_policy"
echo "     terraform state rm module.eks.aws_iam_policy_attachment.eks_nodes_worker_policy"
echo "     terraform state rm module.eks.aws_iam_policy_attachment.eks_nodes_cni_policy"
echo "     terraform state rm module.eks.aws_iam_policy_attachment.eks_nodes_ecr_policy"
echo "  4. terraform plan -var-file=\"prod.tfvars\""
echo "  5. terraform apply -var-file=\"prod.tfvars\""
echo ""
