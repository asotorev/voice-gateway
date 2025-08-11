#!/bin/bash

# Deploy script for Voice Gateway Shared Layer
# Usage: ./deploy.sh [stage] [region]

set -e

# Default values
STAGE=${1:-dev}
REGION=${2:-us-east-1}

echo "Deploying Voice Gateway Shared Layer"
echo "Stage: $STAGE"
echo "Region: $REGION"

# Set deployment environment variables
export STAGE=$STAGE
export AWS_REGION=$REGION

echo "Installing dependencies..."
npm install

echo "Validating serverless configuration..."
npx serverless print --stage $STAGE --region $REGION

echo "Deploying shared layer to AWS..."
npx serverless deploy --stage $STAGE --region $REGION --verbose

echo "SUCCESS: Voice Gateway Shared Layer deployed successfully!"
echo ""
echo "Deployment Summary:"
echo "Stage: $STAGE"
echo "Region: $REGION"
echo "Layers created:"
echo "  - voice-gateway-shared-$STAGE (consolidated layer with shared code + lightweight dependencies)"
echo ""
echo "Next steps:"
echo "  1. Deploy Lambda functions using updated serverless.yml configurations"
echo "  2. Lambda functions will use optimized layers automatically"
echo "  3. Monitor layer usage and performance"
