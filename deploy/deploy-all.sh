#!/bin/bash

# Complete deployment script for Cerca API
set -e

IMAGE_TAG="${1:-latest}"

echo "🚀 Starting complete deployment of Cerca API..."
echo "🏷️  Image tag: ${IMAGE_TAG}"
echo ""

# Check required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY environment variable is required"
    echo "Usage: OPENAI_API_KEY=your-key ./deploy/deploy-all.sh [image-tag]"
    exit 1
fi

# Step 1: Deploy infrastructure
echo "📋 Step 1: Deploying infrastructure..."
./deploy/deploy-infrastructure.sh

# Step 2: Build and push Docker image
echo ""
echo "📋 Step 2: Building and pushing Docker image..."
./deploy/build-and-push.sh ${IMAGE_TAG}

# Step 3: Deploy ECS service
echo ""
echo "📋 Step 3: Deploying ECS service..."
./deploy/deploy-service.sh ${IMAGE_TAG}

echo ""
echo "🎉 Complete deployment finished successfully!"
echo ""
echo "🌐 Your Cerca API is now running on AWS ECS Fargate!"
echo "   Check the CloudFormation stack outputs for the LoadBalancerURL."
echo ""

# Get the load balancer URL
STACK_NAME="cerca-api-infrastructure"
REGION="us-east-1"

LB_URL=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ ! -z "$LB_URL" ]; then
    echo "🔗 API URL: ${LB_URL}"
    echo "🔍 Health check: ${LB_URL}/health"
    echo "📊 Attributes endpoint: ${LB_URL}/api/attributes"
fi