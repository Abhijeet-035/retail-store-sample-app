#!/usr/bin/env bash
# create-ecr-repos.sh
# Creates all required ECR repositories for the retail-store-sample-app CI/CD pipeline

set -euo pipefail

REGION="${1:-$(aws configure get region)}"

if [ -z "${REGION}" ]; then
  echo "Error: AWS region not specified" >&2
  echo "Usage: $0 [AWS_REGION]" >&2
  exit 1
fi

SERVICES=(ui cart catalog checkout orders)

echo "Creating ECR repositories in region: ${REGION}"
echo "================================================"

for SERVICE in "${SERVICES[@]}"; do
  REPO_NAME="retail-store-sample-${SERVICE}"
  echo "Creating: ${REPO_NAME}"

  if aws ecr describe-repositories --repository-names "${REPO_NAME}" --region "${REGION}" &>/dev/null; then
    echo "  ✓ Already exists"
  else
    aws ecr create-repository \
      --repository-name "${REPO_NAME}" \
      --region "${REGION}" \
      --image-scanning-configuration scanOnPush=true \
      --encryption-configuration encryptionType=AES256
    echo "  ✓ Created"
  fi
done

echo "================================================"
echo "Done! Get your account ID with:"
echo "  aws sts get-caller-identity --query Account --output text"
