#!/bin/bash

# Test Docker container locally before deployment
set -e

echo "🧪 Testing Cerca API Docker container locally..."

# Build the Docker image
echo "🏗️  Building Docker image..."
docker build -t cerca-api:test .

# Stop any existing container
echo "🛑 Stopping any existing test container..."
docker stop cerca-api-test 2>/dev/null || true
docker rm cerca-api-test 2>/dev/null || true

# Run the container
echo "🚀 Starting test container..."
docker run -d \
    --name cerca-api-test \
    -p 5001:5000 \
    -e DATABASE_URL="${DATABASE_URL:-postgresql://postgres:cerca123@cerca-aurora-cluster.cluster-cxgooo0scwa0.us-east-1.rds.amazonaws.com:5432/cerca}" \
    -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
    -e FLASK_DEBUG=false \
    cerca-api:test

# Wait for container to start
echo "⏳ Waiting for container to start..."
sleep 10

# Test health endpoint
echo "🔍 Testing health endpoint..."
if curl -f http://localhost:5001/health; then
    echo ""
    echo "✅ Health check passed!"
else
    echo ""
    echo "❌ Health check failed!"
    docker logs cerca-api-test
    exit 1
fi

# Test API endpoint
echo ""
echo "🔍 Testing API endpoint..."
if curl -f "http://localhost:5001/api/attributes?limit=3"; then
    echo ""
    echo "✅ API endpoint test passed!"
else
    echo ""
    echo "❌ API endpoint test failed!"
    docker logs cerca-api-test
    exit 1
fi

# Show container logs
echo ""
echo "📋 Container logs:"
docker logs cerca-api-test --tail 20

# Cleanup
echo ""
echo "🧹 Cleaning up test container..."
docker stop cerca-api-test
docker rm cerca-api-test

echo ""
echo "🎉 Docker container test completed successfully!"
echo "📦 Container is ready for deployment to ECS Fargate."