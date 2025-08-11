#!/bin/bash

# Deploy script for Voice Authentication Processor Lambda
# Usage: ./deploy.sh [stage] [region]

set -e

# Default values
STAGE=${1:-dev}
REGION=${2:-us-east-1}

echo "Deploying Voice Authentication Processor Lambda"
echo "Stage: $STAGE"
echo "Region: $REGION"

# Validate environment variables
if [ -z "$USERS_TABLE_NAME" ]; then
    echo "ERROR: USERS_TABLE_NAME environment variable is required"
    exit 1
fi

# Set deployment environment variables
export STAGE=$STAGE
export AWS_REGION=$REGION
export SERVERLESS_SERVICE_NAME="voice-gateway-auth-lambda"

echo "Installing dependencies..."
npm install

echo "Validating serverless configuration..."
npx serverless print --stage $STAGE --region $REGION

echo "Running tests before deployment..."
# python3 -m pytest tests/ -v

echo "Deploying to AWS..."
npx serverless deploy --stage $STAGE --region $REGION --verbose

echo "SUCCESS: Voice Authentication Processor Lambda deployed successfully!"
echo ""
echo "Deployment Summary:"
echo "Service: $SERVERLESS_SERVICE_NAME"
echo "Stage: $STAGE"
echo "Region: $REGION"
echo "S3 Bucket: voice-gateway-audio-$STAGE (auto-created)"
echo "Users Table: $USERS_TABLE_NAME"
echo ""
echo "Useful commands:"
echo "  View logs: npx serverless logs -f voiceAuthenticationProcessor --stage $STAGE"
echo "  Invoke function: npx serverless invoke -f voiceAuthenticationProcessor --stage $STAGE"
echo "  Remove deployment: npx serverless remove --stage $STAGE"
