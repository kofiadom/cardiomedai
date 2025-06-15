#!/bin/bash

# CardioMed AI Backend Deployment Script
# This script deploys the CardioMed AI backend to Azure Container Instances

set -e  # Exit on any error

# Configuration
RESOURCE_GROUP="cardiomedai-rg"
LOCATION="eastus"
ACR_NAME="cardiomedaiacr"  # Must be globally unique - change this!
CONTAINER_NAME="cardiomedai-backend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting CardioMed AI Backend Deployment${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is logged in to Azure
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to Azure. Please login first.${NC}"
    az login
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Create resource group
echo -e "${YELLOW}📦 Creating resource group: $RESOURCE_GROUP${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION --output table

# Create Azure Container Registry
echo -e "${YELLOW}🏗️  Creating Azure Container Registry: $ACR_NAME${NC}"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true \
    --output table

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
echo -e "${GREEN}✅ ACR Login Server: $ACR_LOGIN_SERVER${NC}"

# Login to ACR
echo -e "${YELLOW}🔐 Logging in to Azure Container Registry${NC}"
az acr login --name $ACR_NAME

# Build Docker image
echo -e "${YELLOW}🔨 Building Docker image${NC}"
docker build -f deployment/Dockerfile.production -t $ACR_LOGIN_SERVER/cardiomedai-backend:latest .

# Push image to ACR
echo -e "${YELLOW}📤 Pushing image to Azure Container Registry${NC}"
docker push $ACR_LOGIN_SERVER/cardiomedai-backend:latest

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)

# Check if environment variables are set
if [ -z "$AZURE_API_KEY" ]; then
    echo -e "${RED}❌ AZURE_API_KEY environment variable is not set${NC}"
    echo -e "${YELLOW}Please set your environment variables:${NC}"
    echo "export AZURE_API_KEY='your_api_key'"
    echo "export AZURE_ENDPOINT='your_endpoint'"
    echo "export AZURE_AI_PROJECT_ENDPOINT='your_project_endpoint'"
    echo "export AZURE_TENANT_ID='your_tenant_id'"
    echo "export AZURE_CLIENT_ID='your_client_id'"
    echo "export AZURE_CLIENT_SECRET='your_client_secret'"
    exit 1
fi

# Deploy container instance
echo -e "${YELLOW}🚀 Deploying container instance${NC}"
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --image $ACR_LOGIN_SERVER/cardiomedai-backend:latest \
    --cpu 1 \
    --memory 2 \
    --registry-login-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --dns-name-label cardiomedai-api \
    --ports 8000 \
    --environment-variables \
        AZURE_API_KEY="$AZURE_API_KEY" \
        AZURE_ENDPOINT="$AZURE_ENDPOINT" \
        AZURE_API_VERSION="2024-02-15-preview" \
        AZURE_DEPLOYMENT="gpt-4o-mini" \
        AZURE_AI_PROJECT_ENDPOINT="$AZURE_AI_PROJECT_ENDPOINT" \
        AZURE_TENANT_ID="$AZURE_TENANT_ID" \
        AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
        AZURE_CLIENT_SECRET="$AZURE_CLIENT_SECRET" \
    --output table

# Get deployment information
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo -e "${YELLOW}📋 Getting deployment information...${NC}"

FQDN=$(az container show \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --query ipAddress.fqdn \
    --output tsv)

IP=$(az container show \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --query ipAddress.ip \
    --output tsv)

echo -e "${GREEN}🎉 CardioMed AI Backend Successfully Deployed!${NC}"
echo -e "${GREEN}🌐 API URL: http://$FQDN:8000${NC}"
echo -e "${GREEN}📍 IP Address: $IP${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Test the API: curl http://$FQDN:8000/"
echo "2. View logs: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo "3. Monitor: az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo ""
echo -e "${YELLOW}🔧 Management Commands:${NC}"
echo "• View logs: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo "• Restart: az container restart --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo "• Delete: az container delete --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --yes"
echo "• Delete all: az group delete --name $RESOURCE_GROUP --yes"

# Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
sleep 30  # Wait for container to start
if curl -f http://$FQDN:8000/ &> /dev/null; then
    echo -e "${GREEN}✅ API is responding successfully!${NC}"
else
    echo -e "${RED}❌ API is not responding. Check logs for issues.${NC}"
    echo "Run: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
fi