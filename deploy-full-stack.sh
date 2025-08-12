#!/bin/bash

# Voice Gateway - Full Stack Deployment
# Deploys complete Voice Gateway infrastructure in correct order

set -euo pipefail

STAGE="${STAGE:-prod}"
REGION="${AWS_REGION:-us-east-1}"

echo "Starting full Voice Gateway deployment..."
echo "Stage: $STAGE | Region: $REGION"
echo ""

# 1. Deploy Shared Layer
echo "1. Deploying shared layer..."
cd app/infrastructure/lambda/shared_layer
./deploy.sh --stage $STAGE
echo ""

# 2. Deploy Audio Embedding Processor
echo "2. Deploying audio embedding processor..."
cd ../audio_embedding_processor/deployment  
./deploy.sh --stage $STAGE
echo ""

# 3. Deploy Voice Authentication Processor
echo "3. Deploying voice authentication processor..."
cd ../../voice_authentication_processor/deployment
./deploy.sh --stage $STAGE
echo ""

# 4. Verify Lambda Functions
echo "4. Verifying Lambda functions..."
cd ../../../../  # Back to project root
aws lambda list-functions --query "Functions[?contains(FunctionName, 'voice-gateway-lambda-$STAGE')].FunctionName" --output table
echo ""

# 5. Deploy App Runner
echo "5. Deploying FastAPI to App Runner..."
./deploy-apprunner.sh
echo ""

echo "Full stack deployment completed!"
