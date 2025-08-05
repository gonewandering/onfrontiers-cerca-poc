#!/bin/bash

# Deploy ECS service
set -e

# Configuration
REGION="us-east-1"
ACCOUNT_ID="471112664201"
REPOSITORY_NAME="cerca-api"
IMAGE_TAG="${1:-latest}"
CLUSTER_NAME="cerca-cluster"
SERVICE_NAME="cerca-api-service"

# ECR repository URI
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPOSITORY_NAME}"

echo "🚀 Deploying Cerca API service..."
echo "📍 Region: ${REGION}"
echo "🖼️  Image: ${ECR_URI}:${IMAGE_TAG}"
echo "🔧 Cluster: ${CLUSTER_NAME}"
echo "⚙️  Service: ${SERVICE_NAME}"

# Check if task definition file exists (updated with correct image)
TASK_DEF_FILE="deploy/ecs/task-definition-updated.json"
if [ ! -f "$TASK_DEF_FILE" ]; then
    echo "📝 Updating task definition with image URI..."
    sed "s|cerca-api:latest|${ECR_URI}:${IMAGE_TAG}|g" deploy/ecs/task-definition.json > ${TASK_DEF_FILE}
fi

# Register new task definition
echo "📝 Registering new task definition..."
TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
    --region ${REGION} \
    --cli-input-json file://${TASK_DEF_FILE} \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✅ Registered task definition: ${TASK_DEFINITION_ARN}"

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services \
    --region ${REGION} \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME} \
    --query 'services[0].status' \
    --output text 2>/dev/null || echo "None")

if [ "$SERVICE_EXISTS" = "None" ] || [ "$SERVICE_EXISTS" = "INACTIVE" ]; then
    echo "🆕 Creating new ECS service..."
    
    # Create service
    aws ecs create-service \
        --region ${REGION} \
        --cluster ${CLUSTER_NAME} \
        --service-name ${SERVICE_NAME} \
        --task-definition ${TASK_DEFINITION_ARN} \
        --desired-count 2 \
        --launch-type FARGATE \
        --platform-version LATEST \
        --network-configuration "awsvpcConfiguration={subnets=[subnet-0c988bae329f14d31,subnet-0af6aca7def3cff9f],securityGroups=[sg-095943a923fded506],assignPublicIp=ENABLED}" \
        --health-check-grace-period-seconds 120 \
        --deployment-configuration "maximumPercent=200,minimumHealthyPercent=50,deploymentCircuitBreaker={enable=true,rollback=true}" \
        --tags key=Environment,value=production key=Service,value=cerca-api
        
    echo "✅ ECS service created successfully!"
else
    echo "🔄 Updating existing ECS service..."
    
    # Update service
    aws ecs update-service \
        --region ${REGION} \
        --cluster ${CLUSTER_NAME} \
        --service ${SERVICE_NAME} \
        --task-definition ${TASK_DEFINITION_ARN} \
        --force-new-deployment
        
    echo "✅ ECS service updated successfully!"
fi

# Wait for deployment to complete
echo "⏳ Waiting for deployment to complete..."
aws ecs wait services-stable \
    --region ${REGION} \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME}

# Get service status
echo ""
echo "📊 Service status:"
aws ecs describe-services \
    --region ${REGION} \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME} \
    --query 'services[0].{ServiceName:serviceName,Status:status,RunningCount:runningCount,DesiredCount:desiredCount}' \
    --output table

echo ""
echo "✅ Service deployment completed successfully!"
echo ""
echo "🌐 Your API should be accessible via the Application Load Balancer DNS name."
echo "   Check the CloudFormation stack outputs for the LoadBalancerURL."