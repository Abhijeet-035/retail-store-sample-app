# Retail Store Terraform Infrastructure

This directory contains the Terraform configuration for deploying the retail store application infrastructure on AWS EKS.

## 📁 File Structure

```
terraform-organized/
├── main.tf                    # Primary infrastructure (VPC, EKS)
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── versions.tf                # Provider requirements and configurations
├── locals.tf                  # Local values and data sources
├── security.tf                # Security groups and rules
├── addons.tf                  # EKS add-ons (NGINX, cert-manager)
├── argocd.tf                  # ArgoCD installation
└── README.md                  # This file
```

## 🚀 Quick Start

### 1. Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0 installed
- kubectl installed

### 2. Configuration

```bash
# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit the variables file with your preferred settings
vim terraform.tfvars
```

**Note**: The cluster name will automatically have a random 4-character suffix added (e.g., `retail-store-a1b2`) to prevent resource conflicts and ensure uniqueness.

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the complete configuration
terraform apply
```

### 4. Configure kubectl

```bash
# Update kubeconfig (replace with your region and cluster name)
aws eks update-kubeconfig --region us-west-2 --name retail-store
```

### 5. Access ArgoCD

```bash
# Get ArgoCD admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d

# Port-forward to ArgoCD server
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Open browser to https://localhost:8080
# Username: admin
# Password: (from step 1)
```

## 📋 What Gets Deployed

### Core Infrastructure
- **VPC** with public and private subnets across 3 AZs
- **EKS Cluster** with Auto Mode enabled
- **Security Groups** with appropriate rules

### Add-ons
- **NGINX Ingress Controller** for load balancing
- **Cert Manager** for SSL certificate management
- **ArgoCD** for GitOps deployment

### Applications (via ArgoCD)
- Retail Store microservices (UI, Catalog, Cart, Orders, Checkout)

## 🔧 Customization

### Variables


```hcl
aws_region                = "us-west-2"
cluster_name              = "retail-store"        # Will have random suffix added
environment               = "dev"
kubernetes_version        = "1.33"
vpc_cidr                  = "10.0.0.0/16"
enable_single_nat_gateway = true    # Set to false for production
enable_monitoring         = false   # Set to true to enable monitoring
```

### Conflict Prevention

This configuration automatically prevents resource conflicts by:
- Adding a random 4-character suffix to cluster names
- Using unique KMS key aliases
- Ensuring resource names don't collide with previous deployments

### Adding More Add-ons

Edit `addons.tf` to enable additional EKS add-ons:

```hcl
# Enable AWS Load Balancer Controller
enable_aws_load_balancer_controller = true

# Enable monitoring stack
enable_kube_prometheus_stack = true
```

## 🏗️ Architecture

```
Internet
    │
    ▼
┌─────────────────┐
│   ALB/NLB       │
│  (via NGINX)    │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   EKS Cluster   │
│  (Auto Mode)    │
│                 │
│  ┌───────────┐  │
│  │  Retail   │  │
│  │   Store   │  │
│  │   Apps    │  │
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │  ArgoCD   │  │
│  └───────────┘  │
└─────────────────┘
```

## 🧹 Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Note**: This will delete all resources including the EKS cluster and VPC. Make sure to backup any important data first.

