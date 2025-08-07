#!/bin/bash

# Voice Gateway Lambda Deployment Script
# Handles deployment of audio processing Lambda functions across environments

set -e  # Exit on any error

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# Default values
STAGE="dev"
REGION="us-east-1"
VERBOSE=false
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
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
    exit 1
}

show_help() {
    cat << EOF
Voice Gateway Lambda Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -s, --stage STAGE       Deployment stage (dev/staging/prod) [default: dev]
    -r, --region REGION     AWS region [default: us-east-1]
    -v, --verbose           Enable verbose output
    -d, --dry-run          Show what would be deployed without actually deploying
    -h, --help             Show this help message

Examples:
    $0                      # Deploy to dev environment
    $0 -s staging -r us-west-2
    $0 --stage prod --verbose
    $0 --dry-run            # Preview deployment

Environment Variables:
    AWS_PROFILE            AWS profile to use for deployment
    AWS_ACCESS_KEY_ID      AWS access key (if not using profile)
    AWS_SECRET_ACCESS_KEY  AWS secret key (if not using profile)
    
    Configuration is loaded from .env.local or environment variables
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stage)
            STAGE="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            ;;
    esac
done

# Validate stage
if [[ ! "$STAGE" =~ ^(dev|staging|prod)$ ]]; then
    log_error "Invalid stage: $STAGE. Must be one of: dev, staging, prod"
fi

# Load environment variables
load_environment() {
    log_info "Loading environment configuration..."
    
    # Look for .env files in project root
    local env_files=(
        "$PROJECT_ROOT/.env.local"
        "$PROJECT_ROOT/.env.$STAGE"
        "$PROJECT_ROOT/.env"
    )
    
    for env_file in "${env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            log_info "Loading environment from: $env_file"
            set -a  # automatically export all variables
            source "$env_file"
            set +a
            break
        fi
    done
    
    # Override with command line values
    export STAGE="$STAGE"
    export AWS_REGION="$REGION"
    
    # Validate required environment variables
    local required_vars=(
        "S3_BUCKET_NAME"
        "USERS_TABLE_NAME"
        "LAMBDA_FUNCTION_NAME"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Required environment variable not set: $var"
        fi
    done
    
    log_success "Environment configuration loaded"
    
    # Debug: Show final configuration values
    if [[ "$VERBOSE" == true ]]; then
        log_info "=== FINAL CONFIGURATION ==="
        log_info "STAGE: $STAGE"
        log_info "AWS_REGION: $AWS_REGION"
        log_info "S3_BUCKET_NAME: ${S3_BUCKET_NAME:-'NOT SET'}"
        log_info "USERS_TABLE_NAME: ${USERS_TABLE_NAME:-'NOT SET'}"
        log_info "LAMBDA_FUNCTION_NAME: ${LAMBDA_FUNCTION_NAME:-'NOT SET'}"
        log_info "SERVERLESS_SERVICE_NAME: ${SERVERLESS_SERVICE_NAME:-'NOT SET'}"
        log_info "=========================="
    fi
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check if serverless is installed
    if ! command -v serverless &> /dev/null; then
        log_error "Serverless Framework not found. Please install: npm install -g serverless"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please set up AWS CLI or environment variables"
    fi
    
    # Check if required files exist
    local required_files=(
        "$SCRIPT_DIR/serverless.yml"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required file not found: $file"
        fi
    done
    
    # Check if S3 bucket exists
    if ! aws s3api head-bucket --bucket "$S3_BUCKET_NAME" --region "$AWS_REGION" &> /dev/null; then
        log_warning "S3 bucket '$S3_BUCKET_NAME' does not exist or is not accessible"
        log_info "You may need to create it manually or ensure proper permissions"
    fi
    
    log_success "Pre-deployment checks passed"
}

# Deploy Lambda function
deploy_lambda() {
    log_info "Deploying Lambda function to stage: $STAGE, region: $AWS_REGION"
    log_info "Function: ${LAMBDA_FUNCTION_NAME:-audio-embedding-processor}"
    log_info "S3 Bucket: $S3_BUCKET_NAME"
    log_info "DynamoDB Table: $USERS_TABLE_NAME"
    
    cd "$SCRIPT_DIR"
    
    local deploy_cmd="serverless deploy --stage $STAGE --region $AWS_REGION"
    
    if [[ "$VERBOSE" == true ]]; then
        deploy_cmd="$deploy_cmd --verbose"
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN - would execute: $deploy_cmd"
        log_info "Would deploy with configuration:"
        serverless print --stage "$STAGE" --region "$AWS_REGION"
        return
    fi
    
    eval "$deploy_cmd"
    
    if [[ $? -eq 0 ]]; then
        log_success "Lambda function deployed successfully"
    else
        log_error "Lambda deployment failed"
    fi
}

# Verify deployment
verify_deployment() {
    if [[ "$DRY_RUN" == true ]]; then
        return
    fi
    
    log_info "Verifying deployment..."
    
    # Get service name from environment or use default
    local service_name="${SERVERLESS_SERVICE_NAME:-voice-gateway-lambda}"
    local function_name="$service_name-$STAGE-audioEmbeddingProcessor"
    
    if aws lambda get-function --function-name "$function_name" --region "$AWS_REGION" &> /dev/null; then
        log_success "Lambda function verified: $function_name"
        
        # Get function configuration
        local function_info=$(aws lambda get-function-configuration --function-name "$function_name" --region "$AWS_REGION")
        local memory_size=$(echo "$function_info" | grep -o '"MemorySize":[0-9]*' | cut -d':' -f2)
        local timeout=$(echo "$function_info" | grep -o '"Timeout":[0-9]*' | cut -d':' -f2)
        
        log_info "Memory: ${memory_size}MB, Timeout: ${timeout}s"
    else
        log_error "Lambda function verification failed: $function_name"
    fi
}

# Main deployment workflow
main() {
    log_info "Starting Voice Gateway Lambda deployment"
    log_info "Stage: $STAGE, Region: $REGION"
    
    load_environment
    pre_deployment_checks
    deploy_lambda
    verify_deployment
    
    log_success "Deployment completed successfully!"
    
    if [[ "$DRY_RUN" == false ]]; then
        local service_name="${SERVERLESS_SERVICE_NAME:-voice-gateway-lambda}"
        local function_name="$service_name-$STAGE-audioEmbeddingProcessor"
        log_info "Function name: $function_name"
        log_info "AWS Console: https://$AWS_REGION.console.aws.amazon.com/lambda/home?region=$AWS_REGION"
    fi
}

# Execute main function
main
