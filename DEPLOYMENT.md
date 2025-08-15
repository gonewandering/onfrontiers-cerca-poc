# Cerca API Deployment Guide

## Quick Deployment

To deploy the latest version of the application:

```bash
./deploy.sh
```

This single command will:
1. ✅ Build a fresh Docker image (--no-cache)
2. ✅ Push it to ECR with a timestamped tag
3. ✅ Create a new ECS task definition
4. ✅ Deploy to the ECS service
5. ✅ Wait for deployment completion
6. ✅ Verify the deployment

## Script Options

```bash
# Show help
./deploy.sh help

# Deploy without waiting for completion
./deploy.sh --no-wait

# Deploy with a custom tag
./deploy.sh --tag my-custom-tag
```

## Manual Deployment Steps

If you prefer to run steps manually:

### 1. Build Docker Image
```bash
# Generate timestamp tag
TAG="v$(date +%Y%m%d-%H%M%S)"

# Build with no cache
docker build --platform linux/amd64 --no-cache -t cerca-api:$TAG .
```

### 2. Push to ECR
```bash
# Authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  471112664201.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag cerca-api:$TAG 471112664201.dkr.ecr.us-east-1.amazonaws.com/cerca-api:$TAG
docker push 471112664201.dkr.ecr.us-east-1.amazonaws.com/cerca-api:$TAG
```

### 3. Update Task Definition
```bash
# Update the image in task definition file
sed -i "s|\"image\": \"471112664201.dkr.ecr.us-east-1.amazonaws.com/cerca-api:.*\"|\"image\": \"471112664201.dkr.ecr.us-east-1.amazonaws.com/cerca-api:$TAG\"|g" deploy/ecs/task-definition-fixed.json

# Register new task definition
aws ecs register-task-definition \
  --region us-east-1 \
  --cli-input-json file://deploy/ecs/task-definition-fixed.json
```

### 4. Deploy to ECS
```bash
# Get the new task definition ARN and deploy
TASK_DEF=$(aws ecs describe-task-definition --region us-east-1 --task-definition cerca-api --query 'taskDefinition.taskDefinitionArn' --output text)

aws ecs update-service \
  --region us-east-1 \
  --cluster cerca-cluster \
  --service cerca-api-service \
  --task-definition $TASK_DEF \
  --force-new-deployment
```

## Monitoring Deployment

### Check Deployment Status
```bash
aws ecs describe-services \
  --region us-east-1 \
  --cluster cerca-cluster \
  --services cerca-api-service \
  --query 'services[0].deployments[*].{Status:status,TaskDefinition:taskDefinition,RolloutState:rolloutState,RunningCount:runningCount}' \
  --output table
```

### Check Application Health
```bash
curl -s "http://cerca-alb-817048840.us-east-1.elb.amazonaws.com/health" | jq .
```

### Check Service Events
```bash
aws ecs describe-services \
  --region us-east-1 \
  --cluster cerca-cluster \
  --services cerca-api-service \
  --query 'services[0].events[0:5]'
```

## Prerequisites

- Docker installed and running
- AWS CLI installed and configured
- Appropriate AWS permissions for ECS, ECR, and CloudFormation
- `jq` installed (for JSON parsing)

## Troubleshooting

### Common Issues

1. **Docker build fails**: Ensure Docker is running and you have sufficient disk space
2. **ECR push timeout**: Check your internet connection; the script will retry automatically
3. **Task definition registration fails**: Verify the task definition JSON is valid
4. **Deployment fails**: Check ECS service events and task logs in CloudWatch

### Getting Logs
```bash
# Get recent service events
aws ecs describe-services \
  --region us-east-1 \
  --cluster cerca-cluster \
  --services cerca-api-service \
  --query 'services[0].events[0:10]'

# Get task logs (replace TASK_ID)
aws logs get-log-events \
  --region us-east-1 \
  --log-group-name /ecs/cerca-api \
  --log-stream-name ecs/cerca-api/TASK_ID
```

## Environment

- **Region**: us-east-1
- **ECR Repository**: 471112664201.dkr.ecr.us-east-1.amazonaws.com/cerca-api
- **ECS Cluster**: cerca-cluster
- **ECS Service**: cerca-api-service
- **Task Family**: cerca-api
- **Load Balancer**: http://cerca-alb-817048840.us-east-1.elb.amazonaws.com