#!/bin/bash

# Cerca API Deployment Script
# Builds, pushes, and deploys the application to AWS ECS

set -e  # Exit on any error

# Configuration
REGION="us-east-1"
ACCOUNT_ID="471112664201"
ECR_REPO="cerca-api"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"
CLUSTER_NAME="cerca-cluster"
SERVICE_NAME="cerca-api-service"
TASK_FAMILY="cerca-api"
TASK_DEF_FILE="deploy/ecs/task-definition-fixed.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it and try again."
        exit 1
    fi
    
    # Check if task definition file exists
    if [ ! -f "$TASK_DEF_FILE" ]; then
        log_error "Task definition file not found: $TASK_DEF_FILE"
        exit 1
    fi
}

# Generate unique image tag
generate_tag() {
    echo "v$(date +%Y%m%d-%H%M%S)"
}

# Authenticate with ECR
authenticate_ecr() {
    echo "Authenticating with ECR..."
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI >/dev/null 2>&1
    log_success "ECR authenticated"
}

# Build Docker image
build_image() {
    local tag=$1
    echo "Building Docker image: $tag"
    
    docker build --platform linux/amd64 --no-cache -t ${ECR_REPO}:${tag} . >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Image built: ${ECR_REPO}:${tag}"
    else
        log_error "Docker build failed"
        exit 1
    fi
}

# Push image to ECR
push_image() {
    local tag=$1
    echo "Pushing to ECR..."
    docker tag ${ECR_REPO}:${tag} ${ECR_URI}:${tag}
    docker push ${ECR_URI}:${tag} >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Image pushed to ECR"
    else
        log_error "Failed to push image to ECR"
        exit 1
    fi
}

# Update task definition with new image
update_task_definition() {
    local tag=$1
    local temp_file=$(mktemp)
    
    echo "Updating task definition..."
    
    # Update the image URI in task definition
    sed "s|\"image\": \"${ECR_URI}:.*\"|\"image\": \"${ECR_URI}:${tag}\"|g" $TASK_DEF_FILE > $temp_file
    
    # Register new task definition
    local task_def_arn=$(aws ecs register-task-definition \
        --region $REGION \
        --cli-input-json file://$temp_file \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        log_success "Task definition registered"
        echo $task_def_arn
    else
        log_error "Failed to register task definition"
        exit 1
    fi
    
    # Cleanup temp file
    rm $temp_file
}

# Deploy to ECS
deploy_to_ecs() {
    local task_def_arn=$1
    
    echo "Deploying to ECS..."
    
    aws ecs update-service \
        --region $REGION \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition $task_def_arn \
        --force-new-deployment >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Deployment initiated"
    else
        log_error "Failed to deploy to ECS"
        exit 1
    fi
}

# Wait for deployment to complete
wait_for_deployment() {
    log_info "Waiting for deployment to complete..."
    log_warning "This may take several minutes..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local rollout_state=$(aws ecs describe-services \
            --region $REGION \
            --cluster $CLUSTER_NAME \
            --services $SERVICE_NAME \
            --query 'services[0].deployments[0].rolloutState' \
            --output text)
        
        if [ "$rollout_state" = "COMPLETED" ]; then
            log_success "Deployment completed successfully!"
            return 0
        elif [ "$rollout_state" = "FAILED" ]; then
            log_error "Deployment failed!"
            return 1
        else
            echo -n "."
            sleep 10
            ((attempt++))
        fi
    done
    
    log_warning "Deployment is still in progress. Check AWS console for status."
    return 0
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Get ALB URL from CloudFormation stack
    local alb_url=$(aws cloudformation describe-stacks \
        --region $REGION \
        --query 'Stacks[?StackName==`cerca-infrastructure`].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
        --output text 2>/dev/null)
    
    if [ -n "$alb_url" ]; then
        log_info "Testing health endpoint: ${alb_url}/health"
        local health_status=$(curl -s "${alb_url}/health" | jq -r '.status' 2>/dev/null)
        
        if [ "$health_status" = "healthy" ]; then
            log_success "Health check passed!"
            log_info "Application is available at: ${alb_url}/ui/search"
        else
            log_warning "Health check failed or endpoint not responding"
        fi
    else
        log_info "ALB URL not found in CloudFormation. Check manually:"
        log_info "http://cerca-alb-817048840.us-east-1.elb.amazonaws.com/health"
    fi
}

# Clean up old Docker images
cleanup_images() {
    log_info "Cleaning up old Docker images..."
    docker image prune -f >/dev/null 2>&1 || true
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting Cerca API deployment..."
    
    # Generate unique tag
    TAG=$(generate_tag)
    log_info "Using deployment tag: $TAG"
    
    # Run deployment steps
    check_prerequisites
    authenticate_ecr
    build_image $TAG
    push_image $TAG
    TASK_DEF_ARN=$(update_task_definition $TAG)
    deploy_to_ecs $TASK_DEF_ARN
    wait_for_deployment
    verify_deployment
    cleanup_images
    
    log_success "Deployment completed successfully!"
    log_info "New image tag: $TAG"
    log_info "Task definition: $TASK_DEF_ARN"
}

# Handle script arguments
case "${1:-}" in
    "help"|"-h"|"--help")
        echo "Cerca API Deployment Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  help, -h, --help    Show this help message"
        echo "  --no-wait          Skip waiting for deployment completion"
        echo "  --tag TAG          Use specific tag instead of auto-generated"
        echo ""
        echo "This script will:"
        echo "  1. Build a fresh Docker image (--no-cache)"
        echo "  2. Push it to ECR with a timestamped tag"
        echo "  3. Create a new ECS task definition"
        echo "  4. Deploy to the ECS service"
        echo "  5. Wait for deployment completion"
        echo "  6. Verify the deployment"
        exit 0
        ;;
    "--no-wait")
        SKIP_WAIT=true
        ;;
    "--tag")
        if [ -z "$2" ]; then
            log_error "Tag value required after --tag option"
            exit 1
        fi
        CUSTOM_TAG="$2"
        ;;
esac

# Override functions if needed
if [ "$SKIP_WAIT" = true ]; then
    wait_for_deployment() {
        log_info "Skipping deployment wait (--no-wait specified)"
    }
fi

if [ -n "$CUSTOM_TAG" ]; then
    generate_tag() {
        echo "$CUSTOM_TAG"
    }
fi

# Run main function
main