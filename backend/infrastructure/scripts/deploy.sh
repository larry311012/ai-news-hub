#!/bin/bash
# ============================================================================
# AWS Deployment Script - AI Post Generator
# ============================================================================
# This script automates the deployment of the AI Post Generator to AWS
# Usage: ./deploy.sh [environment]
#   environment: dev, staging, or production (default: production)
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
PROJECT_NAME="ai-post-gen"
AWS_REGION="us-east-1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$ROOT_DIR/terraform"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials are not configured. Please run 'aws configure'."
        exit 1
    fi

    log_success "All prerequisites met"
}

setup_terraform_backend() {
    log_info "Setting up Terraform backend..."

    BUCKET_NAME="${PROJECT_NAME}-terraform-state"

    # Check if bucket exists
    if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
        log_info "Creating S3 bucket for Terraform state..."
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$AWS_REGION"

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "$BUCKET_NAME" \
            --versioning-configuration Status=Enabled

        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "$BUCKET_NAME" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'

        log_success "S3 bucket created: $BUCKET_NAME"
    else
        log_info "S3 bucket already exists: $BUCKET_NAME"
    fi

    # Check if DynamoDB table exists
    if ! aws dynamodb describe-table --table-name terraform-state-locks &> /dev/null; then
        log_info "Creating DynamoDB table for state locking..."
        aws dynamodb create-table \
            --table-name terraform-state-locks \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION"

        log_success "DynamoDB table created: terraform-state-locks"
    else
        log_info "DynamoDB table already exists: terraform-state-locks"
    fi
}

generate_secrets() {
    log_info "Generating and storing secrets..."

    # Generate encryption key
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

    # Store in Secrets Manager
    SECRET_NAME="${PROJECT_NAME}/${ENVIRONMENT}/encryption-key"

    if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" &> /dev/null; then
        log_info "Updating existing secret: $SECRET_NAME"
        aws secretsmanager update-secret \
            --secret-id "$SECRET_NAME" \
            --secret-string "$ENCRYPTION_KEY"
    else
        log_info "Creating new secret: $SECRET_NAME"
        aws secretsmanager create-secret \
            --name "$SECRET_NAME" \
            --secret-string "$ENCRYPTION_KEY" \
            --description "Encryption key for user API keys and sensitive data"
    fi

    log_success "Secrets configured"
}

init_terraform() {
    log_info "Initializing Terraform..."

    cd "$TERRAFORM_DIR"

    terraform init \
        -backend-config="bucket=${PROJECT_NAME}-terraform-state" \
        -backend-config="key=${ENVIRONMENT}/terraform.tfstate" \
        -backend-config="region=${AWS_REGION}"

    log_success "Terraform initialized"
}

plan_terraform() {
    log_info "Planning Terraform deployment..."

    cd "$TERRAFORM_DIR"

    terraform plan \
        -var-file="environments/${ENVIRONMENT}.tfvars" \
        -out="${ENVIRONMENT}.tfplan"

    log_success "Terraform plan created: ${ENVIRONMENT}.tfplan"
}

apply_terraform() {
    log_info "Applying Terraform configuration..."

    cd "$TERRAFORM_DIR"

    # Ask for confirmation
    echo ""
    log_warning "This will deploy infrastructure to AWS. This may incur costs."
    read -p "Do you want to proceed? (yes/no): " -r
    echo

    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi

    terraform apply "${ENVIRONMENT}.tfplan"

    log_success "Infrastructure deployed successfully"
}

build_docker_image() {
    log_info "Building Docker image..."

    cd "$ROOT_DIR/../.."  # Go to backend directory

    IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")

    docker build -t "${PROJECT_NAME}-backend:${IMAGE_TAG}" .

    log_success "Docker image built: ${PROJECT_NAME}-backend:${IMAGE_TAG}"
}

push_docker_image() {
    log_info "Pushing Docker image to ECR..."

    # Get ECR repository URL
    ECR_URL=$(aws ecr describe-repositories \
        --repository-names "${PROJECT_NAME}-backend" \
        --query 'repositories[0].repositoryUri' \
        --output text 2>/dev/null)

    if [ -z "$ECR_URL" ]; then
        log_error "ECR repository not found. Please deploy infrastructure first."
        exit 1
    fi

    IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")

    # Login to ECR
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_URL"

    # Tag and push
    docker tag "${PROJECT_NAME}-backend:${IMAGE_TAG}" "${ECR_URL}:${IMAGE_TAG}"
    docker tag "${PROJECT_NAME}-backend:${IMAGE_TAG}" "${ECR_URL}:latest"

    docker push "${ECR_URL}:${IMAGE_TAG}"
    docker push "${ECR_URL}:latest"

    log_success "Docker image pushed to ECR: ${ECR_URL}:${IMAGE_TAG}"
}

deploy_application() {
    log_info "Deploying application to ECS..."

    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

    # Update ECS service to force new deployment
    aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$SERVICE_NAME" \
        --force-new-deployment \
        --region "$AWS_REGION" \
        > /dev/null

    log_info "Waiting for service to stabilize..."

    aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION"

    log_success "Application deployed successfully"
}

run_smoke_tests() {
    log_info "Running smoke tests..."

    # Get ALB DNS name
    ALB_DNS=$(cd "$TERRAFORM_DIR" && terraform output -raw alb_dns_name 2>/dev/null)

    if [ -z "$ALB_DNS" ]; then
        log_warning "Could not get ALB DNS name. Skipping smoke tests."
        return
    fi

    API_URL="https://$ALB_DNS"

    # Test health endpoint
    log_info "Testing health endpoint: $API_URL/health"

    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" || echo "000")

    if [ "$RESPONSE" = "200" ]; then
        log_success "Health check passed"
    else
        log_error "Health check failed with status code: $RESPONSE"
        return 1
    fi

    # Test API endpoint
    log_info "Testing API endpoint: $API_URL/api"

    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api" || echo "000")

    if [ "$RESPONSE" = "200" ]; then
        log_success "API check passed"
    else
        log_warning "API check returned status code: $RESPONSE"
    fi

    log_success "Smoke tests completed"
}

show_outputs() {
    log_info "Deployment outputs:"
    echo ""

    cd "$TERRAFORM_DIR"

    echo "=========================================="
    echo "Deployment Information"
    echo "=========================================="
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo ""

    terraform output -json | jq -r 'to_entries[] | "\(.key): \(.value.value)"' 2>/dev/null || \
        terraform output

    echo ""
    echo "=========================================="
    echo "Next Steps"
    echo "=========================================="
    echo "1. Configure DNS to point to the ALB"
    echo "2. Set up SSL certificate validation"
    echo "3. Configure monitoring alerts"
    echo "4. Review CloudWatch dashboards"
    echo "5. Run full integration tests"
    echo ""
}

# Main deployment flow
main() {
    echo ""
    echo "=========================================="
    echo "AI Post Generator - AWS Deployment"
    echo "=========================================="
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo "=========================================="
    echo ""

    check_prerequisites

    # Infrastructure deployment
    log_info "Starting infrastructure deployment..."
    setup_terraform_backend
    generate_secrets
    init_terraform
    plan_terraform
    apply_terraform

    # Application deployment
    log_info "Starting application deployment..."
    build_docker_image
    push_docker_image
    deploy_application

    # Post-deployment
    run_smoke_tests
    show_outputs

    log_success "Deployment completed successfully!"
    echo ""
}

# Run main function
main
