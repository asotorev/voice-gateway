#!/bin/bash

# Voice Gateway - AWS App Runner Deployment Script
# Deploys FastAPI container to App Runner with proper environment configuration

set -euo pipefail

# Configuration
SERVICE_NAME="voice-gateway-api"
REGION="${AWS_REGION:-us-east-1}"
STAGE="${STAGE:-prod}"
IMAGE_REPOSITORY_TYPE="ECR"  # or "ECR_PUBLIC"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create ECR repository if it doesn't exist
create_ecr_repository() {
    local repo_name="$SERVICE_NAME-$STAGE"
    
    log_info "Checking ECR repository: $repo_name"
    
    if ! aws ecr describe-repositories --repository-names "$repo_name" --region "$REGION" &> /dev/null; then
        log_info "Creating ECR repository: $repo_name"
        aws ecr create-repository \
            --repository-name "$repo_name" \
            --region "$REGION" \
            --image-scanning-configuration scanOnPush=true
        log_success "ECR repository created: $repo_name"
    else
        log_info "ECR repository already exists: $repo_name"
    fi
    
    # Get repository URI
    ECR_URI=$(aws ecr describe-repositories \
        --repository-names "$repo_name" \
        --region "$REGION" \
        --query 'repositories[0].repositoryUri' \
        --output text)
    
    log_info "ECR Repository URI: $ECR_URI"
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building Docker image..."
    
    # Get ECR login token
    aws ecr get-login-password --region "$REGION" | \
        docker login --username AWS --password-stdin "$ECR_URI"
    
    # Build image with proper tags
    local image_tag="$ECR_URI:latest"
    local image_tag_versioned="$ECR_URI:$(date +%Y%m%d-%H%M%S)"
    
    docker build -t "$SERVICE_NAME:latest" .
    docker tag "$SERVICE_NAME:latest" "$image_tag"
    docker tag "$SERVICE_NAME:latest" "$image_tag_versioned"
    
    log_info "Pushing image to ECR..."
    docker push "$image_tag"
    docker push "$image_tag_versioned"
    
    log_success "Image pushed successfully"
    echo "Latest image: $image_tag"
    echo "Versioned image: $image_tag_versioned"
}

# Create App Runner service configuration
create_apprunner_config() {
    cat > apprunner-service-config.json << EOF
{
    "ServiceName": "$SERVICE_NAME-$STAGE",
    "SourceConfiguration": {
        "ImageRepository": {
            "ImageIdentifier": "$ECR_URI:latest",
            "ImageConfiguration": {
                "Port": "8080",
                "RuntimeEnvironmentVariables": {
                    "APP_ENV": "production",
                    "APP_HOST": "0.0.0.0", 
                    "APP_PORT": "8080",
                    "AWS_DEFAULT_REGION": "$REGION",
                    "LOG_LEVEL": "INFO",
                    "USERS_TABLE_NAME": "voice-gateway-users-$STAGE",
                    "S3_BUCKET_NAME": "voice-gateway-audio-$STAGE",
                    "VOICE_AUTH_LAMBDA_FUNCTION_NAME": "voice-gateway-lambda-$STAGE-voiceAuthenticationProcessor",
                    "REGISTRATION_LAMBDA_FUNCTION_NAME": "voice-gateway-lambda-$STAGE-audioEmbeddingProcessor",
                    "ENABLE_VOICE_AUTHENTICATION": "true",
                    "ENABLE_REGISTRATION": "true",
                    "CORS_ORIGINS": "*",
                    "MAX_UPLOAD_SIZE_MB": "10"
                }
            },
            "ImageRepositoryType": "$IMAGE_REPOSITORY_TYPE"
        },
        "AutoDeploymentsEnabled": true
    },
    "InstanceConfiguration": {
        "Cpu": "0.25 vCPU",
        "Memory": "0.5 GB"
    },
    "HealthCheckConfiguration": {
        "Protocol": "HTTP",
        "Path": "/api/ping",
        "Interval": 30,
        "Timeout": 5,
        "HealthyThreshold": 2,
        "UnhealthyThreshold": 3
    }
}
EOF
}

# Deploy or update App Runner service
deploy_apprunner_service() {
    local service_name="$SERVICE_NAME-$STAGE"
    
    log_info "Checking if App Runner service exists: $service_name"
    
    if aws apprunner describe-service --service-arn "arn:aws:apprunner:$REGION:$(aws sts get-caller-identity --query Account --output text):service/$service_name" &> /dev/null; then
        log_info "Updating existing App Runner service..."
        
        # Update service with new image
        aws apprunner update-service \
            --service-arn "arn:aws:apprunner:$REGION:$(aws sts get-caller-identity --query Account --output text):service/$service_name" \
            --source-configuration file://apprunner-service-config.json \
            --region "$REGION"
            
        log_success "App Runner service update initiated"
    else
        log_info "Creating new App Runner service..."
        
        # Create new service
        aws apprunner create-service \
            --cli-input-json file://apprunner-service-config.json \
            --region "$REGION"
            
        log_success "App Runner service creation initiated"
    fi
    
    # Wait for service to be ready
    log_info "Waiting for service to be ready (this may take a few minutes)..."
    
    local service_arn="arn:aws:apprunner:$REGION:$(aws sts get-caller-identity --query Account --output text):service/$service_name"
    
    while true; do
        local status=$(aws apprunner describe-service \
            --service-arn "$service_arn" \
            --query 'Service.Status' \
            --output text \
            --region "$REGION")
        
        if [[ "$status" == "RUNNING" ]]; then
            log_success "Service is running!"
            break
        elif [[ "$status" == "CREATE_FAILED" ]] || [[ "$status" == "UPDATE_FAILED" ]]; then
            log_error "Service deployment failed with status: $status"
            exit 1
        else
            log_info "Service status: $status - waiting..."
            sleep 30
        fi
    done
    
    # Get service URL
    local service_url=$(aws apprunner describe-service \
        --service-arn "$service_arn" \
        --query 'Service.ServiceUrl' \
        --output text \
        --region "$REGION")
    
    log_success "Voice Gateway API deployed successfully!"
    echo ""
    echo "Service URL: https://$service_url"
    echo "Health Check: https://$service_url/api/ping"
    echo "API Docs: https://$service_url/docs"
    echo ""
}

# Cleanup temporary files
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f apprunner-service-config.json
}

# Main deployment function
main() {
    log_info "Starting Voice Gateway App Runner deployment..."
    log_info "Service: $SERVICE_NAME-$STAGE"
    log_info "Region: $REGION"
    
    check_prerequisites
    create_ecr_repository
    create_apprunner_config
    build_and_push_image
    deploy_apprunner_service
    cleanup
    
    log_success "Deployment completed successfully!"
}

# Handle script interruption
trap cleanup EXIT

# Run main function
main "$@"
