# Cerca API Deployment Guide

This directory contains all the necessary files to deploy the Cerca API to AWS ECS Fargate.

## Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Docker** installed and running
3. **OpenAI API Key** for embedding generation

## Required AWS Permissions

Your AWS user/role needs the following permissions:
- ECR (create repositories, push/pull images)
- ECS (create clusters, services, task definitions)
- CloudFormation (create/update stacks)
- IAM (create roles and policies)
- EC2 (create security groups, describe subnets/VPCs)
- ElasticLoadBalancing (create load balancers, target groups)
- Secrets Manager (create and read secrets)
- CloudWatch Logs (create log groups)

## Architecture Overview

The deployment creates:
- **ECS Fargate Cluster** with 2 running tasks
- **Application Load Balancer** for external access
- **Auto Scaling** with health checks and circuit breaker
- **Secrets Manager** for secure environment variables
- **CloudWatch Logs** for application logging
- **Security Groups** with proper network isolation

## Quick Deployment

### Option 1: Complete Deployment (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-openai-api-key-here"

# Deploy everything in one command
./deploy/deploy-all.sh
```

### Option 2: Step-by-Step Deployment

```bash
# Step 1: Deploy infrastructure
export OPENAI_API_KEY="your-openai-api-key-here"
./deploy/deploy-infrastructure.sh

# Step 2: Build and push Docker image
./deploy/build-and-push.sh

# Step 3: Deploy ECS service
./deploy/deploy-service.sh
```

## Environment Variables

The deployment uses these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings | Required |
| `DATABASE_URL` | PostgreSQL connection string | Aurora cluster endpoint |

## Deployment Configuration

### ECS Configuration
- **CPU**: 512 (0.5 vCPU)
- **Memory**: 1024 MB (1 GB)
- **Desired Count**: 2 instances
- **Launch Type**: Fargate
- **Network**: Public subnets with internet access

### Load Balancer
- **Type**: Application Load Balancer
- **Scheme**: Internet-facing
- **Health Check**: `/health` endpoint
- **Ports**: 80 (HTTP)

### Auto Scaling
- **Max Capacity**: 200% during deployments
- **Min Healthy**: 50% during deployments
- **Circuit Breaker**: Enabled with automatic rollback

## Monitoring and Logging

- **CloudWatch Logs**: `/ecs/cerca-api`
- **Health Checks**: Container and ALB health checks
- **Metrics**: ECS service metrics available in CloudWatch

## Updating the Application

To deploy a new version:

```bash
# Build and deploy with a specific tag
./deploy/build-and-push.sh v1.1.0
./deploy/deploy-service.sh v1.1.0

# Or use the latest tag (default)
./deploy/build-and-push.sh
./deploy/deploy-service.sh
```

## Accessing the API

After deployment, get the load balancer URL:

```bash
aws cloudformation describe-stacks \
    --stack-name cerca-api-infrastructure \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
    --output text
```

### API Endpoints

- **Health Check**: `GET /health`
- **Attributes Search**: `GET /api/attributes?q=search-term&limit=10`
- **List Attributes**: `GET /api/attributes`
- **Experts**: `GET /api/experts`
- **Experiences**: `GET /api/experiences`

### Example Usage

```bash
# Health check
curl http://your-load-balancer-url/health

# Search for defense agencies
curl "http://your-load-balancer-url/api/attributes?q=defense&limit=5"

# List all attributes
curl "http://your-load-balancer-url/api/attributes?limit=10"
```

## Cost Optimization

The deployment uses:
- **Fargate Spot** (80% weight) for cost savings
- **Fargate On-Demand** (20% weight) for reliability
- **Serverless Aurora** with auto-scaling
- **CloudWatch Logs** with 30-day retention

## Troubleshooting

### Service Won't Start
1. Check CloudWatch logs: `/ecs/cerca-api`
2. Verify secrets are created correctly
3. Check security group allows traffic on port 5000

### Health Check Failures
1. Ensure `/health` endpoint is responding
2. Check container logs for startup issues
3. Verify database connectivity

### Image Build Issues
1. Ensure Docker is running
2. Check ECR permissions
3. Verify Dockerfile syntax

## Security

- **Secrets**: Stored in AWS Secrets Manager
- **Network**: Private subnets for ECS tasks
- **IAM**: Least privilege roles
- **HTTPS**: Configure ALB with SSL certificate (manual step)

## Cleanup

To remove all resources:

```bash
# Delete the CloudFormation stack
aws cloudformation delete-stack --stack-name cerca-api-infrastructure

# Delete ECR repository
aws ecr delete-repository --repository-name cerca-api --force
```

## Files Overview

- `infrastructure.yml` - CloudFormation template for AWS resources
- `task-definition.json` - ECS task definition template
- `service.json` - ECS service configuration template
- `build-and-push.sh` - Docker build and ECR push script
- `deploy-infrastructure.sh` - CloudFormation deployment script
- `deploy-service.sh` - ECS service deployment script
- `deploy-all.sh` - Complete deployment script