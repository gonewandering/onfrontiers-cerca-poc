#!/bin/bash

# Deploy ECS infrastructure using CloudFormation
set -e

# Configuration
STACK_NAME="cerca-api-infrastructure"
REGION="us-east-1"
TEMPLATE_FILE="deploy/ecs/infrastructure.yml"

# Get parameters
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:cerca123@cerca-aurora-cluster.cluster-cxgooo0scwa0.us-east-1.rds.amazonaws.com:5432/cerca}"
OPENAI_API_KEY="${OPENAI_API_KEY}"

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY environment variable is required"
    echo "Usage: OPENAI_API_KEY=your-key ./deploy/deploy-infrastructure.sh"
    exit 1
fi

echo "🚀 Deploying Cerca API infrastructure..."
echo "📍 Region: ${REGION}"
echo "🏗️  Stack: ${STACK_NAME}"
echo "📄 Template: ${TEMPLATE_FILE}"

# Deploy CloudFormation stack
aws cloudformation deploy \
    --template-file ${TEMPLATE_FILE} \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        DatabaseUrl="${DATABASE_URL}" \
        OpenAIApiKey="${OPENAI_API_KEY}" \
    --tags \
        Environment=production \
        Service=cerca-api \
        ManagedBy=cloudformation

# Get stack outputs
echo ""
echo "📊 Stack outputs:"
aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "✅ Infrastructure deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Build and push image: ./deploy/build-and-push.sh"
echo "2. Deploy service: ./deploy/deploy-service.sh"