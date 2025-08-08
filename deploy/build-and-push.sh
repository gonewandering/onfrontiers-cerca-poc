#!/bin/bash

# Build and push Docker image to ECR
set -e

# Configuration
REGION="us-east-1"
ACCOUNT_ID="471112664201"
REPOSITORY_NAME="cerca-api"
IMAGE_TAG="${1:-latest}"

# ECR repository URI
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPOSITORY_NAME}"

echo "🚀 Building and pushing Cerca API Docker image..."
echo "📍 Region: ${REGION}"
echo "🏗️  Repository: ${ECR_URI}"
echo "🏷️  Tag: ${IMAGE_TAG}"

# Authenticate Docker to ECR
echo "🔐 Authenticating Docker to ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Create ECR repository if it doesn't exist
echo "📦 Creating ECR repository if it doesn't exist..."
aws ecr describe-repositories --repository-names ${REPOSITORY_NAME} --region ${REGION} 2>/dev/null || \
aws ecr create-repository --repository-name ${REPOSITORY_NAME} --region ${REGION}

# Build Docker image
echo "🏗️  Building Docker image..."
docker buildx create --use --name cerca_builder 2>/dev/null || true
docker buildx build --platform linux/amd64 -t ${REPOSITORY_NAME}:${IMAGE_TAG} . --load

# Tag image for ECR
echo "🏷️  Tagging image for ECR..."
docker tag ${REPOSITORY_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# Push image to ECR
echo "📤 Pushing image to ECR..."
docker push ${ECR_URI}:${IMAGE_TAG}

# Update task definition with new image
echo "📝 Updating task definition..."
sed "s|cerca-api:latest|${ECR_URI}:${IMAGE_TAG}|g" deploy/ecs/task-definition.json > deploy/ecs/task-definition-updated.json

echo "✅ Build and push completed successfully!"
echo "🎯 Image URI: ${ECR_URI}:${IMAGE_TAG}"
echo ""
echo "Next steps:"
echo "1. Deploy infrastructure: ./deploy/deploy-infrastructure.sh"
echo "2. Deploy service: ./deploy/deploy-service.sh"