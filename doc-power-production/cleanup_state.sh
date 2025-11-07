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
