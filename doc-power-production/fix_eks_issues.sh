#!/bin/bash
#
# Fix EKS Issues:
# 1. Add IRSA for EBS CSI Driver
# 2. Import existing aws-auth configmap
# 3. Remove timeout EBS CSI addon from state
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

TF_DIR="infrastructure/terraform"
EKS_MODULE="${TF_DIR}/modules/eks/main.tf"

echo "=========================================="
echo "Fixing EKS Deployment Issues"
echo "=========================================="
echo ""

# Check if in correct directory
if [ ! -f "$EKS_MODULE" ]; then
    echo -e "${RED}❌ File not found: $EKS_MODULE${NC}"
    echo "Please run this script from your project root directory."
    exit 1
fi

echo -e "${BLUE}Step 1: Backing up files...${NC}"
cp "$EKS_MODULE" "${EKS_MODULE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "${TF_DIR}/main.tf" "${TF_DIR}/main.tf.backup.$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}✅ Backups created${NC}"
echo ""

echo -e "${BLUE}Step 2: Adding EBS CSI Driver IAM Role...${NC}"

# Insert EBS CSI Driver IAM role before the addon resource
cat > /tmp/ebs_csi_iam.tf << 'EOF'

# IAM Role for EBS CSI Driver
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

EOF

# Find line number where ebs_csi_driver addon is defined
LINE_NUM=$(grep -n 'resource "aws_eks_addon" "ebs_csi_driver"' "$EKS_MODULE" | cut -d: -f1)

if [ -n "$LINE_NUM" ]; then
    # Insert the IAM role before the addon
    head -n $((LINE_NUM - 1)) "$EKS_MODULE" > /tmp/eks_main_new.tf
    cat /tmp/ebs_csi_iam.tf >> /tmp/eks_main_new.tf
    tail -n +$LINE_NUM "$EKS_MODULE" >> /tmp/eks_main_new.tf
    mv /tmp/eks_main_new.tf "$EKS_MODULE"
    echo -e "${GREEN}✅ Added EBS CSI IAM role${NC}"
else
    echo -e "${YELLOW}⚠️  Could not find EBS CSI addon resource${NC}"
fi

# Update the EBS CSI addon to include service_account_role_arn
sed -i '/resource "aws_eks_addon" "ebs_csi_driver"/,/^}/ {
    /addon_name[[:space:]]*=/a\  service_account_role_arn = aws_iam_role.ebs_csi_driver.arn
}' "$EKS_MODULE"

echo ""

echo -e "${BLUE}Step 3: Updating aws-auth to use import...${NC}"

# Update main.tf to make aws-auth import-friendly
cat > /tmp/aws_auth_update.txt << 'EOF'
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

  lifecycle {
    ignore_changes = [metadata[0].labels, metadata[0].annotations]
  }
}
EOF

# Replace the aws-auth resource in main.tf
sed -i '/resource "kubernetes_config_map" "aws_auth"/,/^}$/c\
resource "kubernetes_config_map" "aws_auth" {\
  metadata {\
    name      = "aws-auth"\
    namespace = "kube-system"\
  }\
\
  data = {\
    mapRoles = yamlencode([\
      {\
        rolearn  = module.eks.node_role_arn\
        username = "system:node:{{EC2PrivateDNSName}}"\
        groups = [\
          "system:bootstrappers",\
          "system:nodes"\
        ]\
      }\
    ])\
  }\
\
  depends_on = [\
    module.eks.node_group_ready\
  ]\
\
  lifecycle {\
    ignore_changes = [metadata[0].labels, metadata[0].annotations]\
  }\
}' "${TF_DIR}/main.tf"

echo -e "${GREEN}✅ Updated aws-auth configmap${NC}"
echo ""

echo -e "${BLUE}Step 4: Creating state cleanup script...${NC}"

cat > cleanup_state.sh << 'CLEANUP_EOF'
#!/bin/bash
#
# Cleanup Terraform state for failed resources
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd infrastructure/terraform

echo "Removing failed resources from state..."
echo ""

# Remove the timed-out EBS CSI addon
echo -n "Removing EBS CSI addon... "
if terraform state rm 'module.eks.aws_eks_addon.ebs_csi_driver' 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️  Not in state${NC}"
fi

# Remove the conflicting aws-auth configmap
echo -n "Removing aws-auth configmap... "
if terraform state rm 'kubernetes_config_map.aws_auth' 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️  Not in state${NC}"
fi

echo ""
echo "Importing existing aws-auth configmap..."
terraform import 'kubernetes_config_map.aws_auth' kube-system/aws-auth

echo ""
echo -e "${GREEN}✅ State cleaned up${NC}"
echo ""
echo "Next steps:"
echo "  1. terraform plan -var-file=\"prod.tfvars\""
echo "  2. terraform apply -var-file=\"prod.tfvars\""
CLEANUP_EOF

chmod +x cleanup_state.sh
echo -e "${GREEN}✅ Created cleanup_state.sh${NC}"
echo ""

echo "=========================================="
echo "Fixes Applied!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Review the changes:"
echo "   diff ${EKS_MODULE}.backup.* ${EKS_MODULE}"
echo ""
echo "2. Run the state cleanup script:"
echo "   ${BLUE}./cleanup_state.sh${NC}"
echo ""
echo "3. If cleanup fails, manually run:"
echo "   cd infrastructure/terraform"
echo "   terraform state rm 'module.eks.aws_eks_addon.ebs_csi_driver'"
echo "   terraform state rm 'kubernetes_config_map.aws_auth'"
echo "   terraform import 'kubernetes_config_map.aws_auth' kube-system/aws-auth"
echo ""
echo "4. Then apply again:"
echo "   terraform plan -var-file=\"prod.tfvars\""
echo "   terraform apply -var-file=\"prod.tfvars\""
echo ""
