# CardioMed AI Backend Deployment to Azure Container Instances

## Prerequisites

1. **Azure CLI** installed and configured
2. **Docker** installed locally
3. **Azure subscription** with appropriate permissions
4. **Azure Container Registry** (recommended) or Docker Hub account

## Step 1: Prepare Environment Variables

Create a production environment file for Azure deployment:

```bash
# Create deployment directory
mkdir -p deployment
```

Create `deployment/.env.production`:
```env
# Azure OpenAI Configuration
AZURE_API_KEY=your_production_azure_api_key
AZURE_ENDPOINT=your_production_azure_endpoint
AZURE_API_VERSION=2024-02-15-preview
AZURE_DEPLOYMENT=gpt-4o-mini

# Azure AI Projects Configuration
AZURE_AI_PROJECT_ENDPOINT=your_azure_ai_project_endpoint
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret

# Agent IDs (will be created during deployment)
HEALTH_ADVISOR_AGENT_ID=
KNOWLEDGE_AGENT_ID=

# Toolbox Configuration
TOOLBOX_URL=http://toolbox:5000

# Database (will use SQLite in container)
DATABASE_URL=sqlite:///./hypertension.db
```

## Step 2: Create Production Dockerfile

Create `deployment/Dockerfile.production`:
```dockerfile
# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir toml && \
    python -c "import toml; deps = toml.load('pyproject.toml')['project']['dependencies']; print('\n'.join(deps))" > requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY hypertension.db ./hypertension.db
COPY migrate_db.py ./migrate_db.py

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Step 3: Create Azure Container Registry

```bash
# Set variables
RESOURCE_GROUP="cardiomedai-rg"
LOCATION="eastus"
ACR_NAME="cardiomedaiacr"  # Must be globally unique
CONTAINER_NAME="cardiomedai-backend"

# Login to Azure
az login

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"
```

## Step 4: Build and Push Docker Image

```bash
# Login to ACR
az acr login --name $ACR_NAME

# Build the Docker image
docker build -f deployment/Dockerfile.production -t $ACR_LOGIN_SERVER/cardiomedai-backend:latest .

# Push the image to ACR
docker push $ACR_LOGIN_SERVER/cardiomedai-backend:latest

# Verify the image was pushed
az acr repository list --name $ACR_NAME --output table
```

## Step 5: Create Azure Container Instance

Create `deployment/container-instance.yaml`:
```yaml
apiVersion: 2021-03-01
location: eastus
name: cardiomedai-backend
properties:
  containers:
  - name: cardiomedai-app
    properties:
      image: cardiomedaiacr.azurecr.io/cardiomedai-backend:latest
      resources:
        requests:
          cpu: 1.0
          memoryInGb: 2.0
      ports:
      - port: 8000
        protocol: TCP
      environmentVariables:
      - name: AZURE_API_KEY
        secureValue: "your_production_azure_api_key"
      - name: AZURE_ENDPOINT
        value: "your_production_azure_endpoint"
      - name: AZURE_API_VERSION
        value: "2024-02-15-preview"
      - name: AZURE_DEPLOYMENT
        value: "gpt-4o-mini"
      - name: AZURE_AI_PROJECT_ENDPOINT
        value: "your_azure_ai_project_endpoint"
      - name: AZURE_TENANT_ID
        secureValue: "your_tenant_id"
      - name: AZURE_CLIENT_ID
        secureValue: "your_client_id"
      - name: AZURE_CLIENT_SECRET
        secureValue: "your_client_secret"
      - name: TOOLBOX_URL
        value: "http://localhost:5000"
  - name: toolbox
    properties:
      image: us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:0.6.0
      resources:
        requests:
          cpu: 0.5
          memoryInGb: 1.0
      ports:
      - port: 5000
        protocol: TCP
      command:
      - /toolbox
      - --tools-file
      - /tools.yaml
      - --address
      - 0.0.0.0
      volumeMounts:
      - name: tools-config
        mountPath: /tools.yaml
        subPath: tools.yaml
      - name: database
        mountPath: /app/hypertension.db
        subPath: hypertension.db
  imageRegistryCredentials:
  - server: cardiomedaiacr.azurecr.io
    username: cardiomedaiacr
    password: "ACR_PASSWORD_HERE"
  ipAddress:
    type: Public
    ports:
    - protocol: TCP
      port: 8000
    dnsNameLabel: cardiomedai-backend
  osType: Linux
  restartPolicy: Always
  volumes:
  - name: tools-config
    configMap:
      name: tools-config
  - name: database
    emptyDir: {}
tags:
  environment: production
  application: cardiomedai
type: Microsoft.ContainerInstance/containerGroups
```

## Step 6: Deploy Using Azure CLI

```bash
# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)

# Create the container instance
az container create \
    --resource-group $RESOURCE_GROUP \
    --name cardiomedai-backend \
    --image $ACR_LOGIN_SERVER/cardiomedai-backend:latest \
    --cpu 1 \
    --memory 2 \
    --registry-login-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --dns-name-label cardiomedai-backend \
    --ports 8000 \
    --environment-variables \
        AZURE_API_KEY="$AZURE_API_KEY" \
        AZURE_ENDPOINT="$AZURE_ENDPOINT" \
        AZURE_API_VERSION="2024-02-15-preview" \
        AZURE_DEPLOYMENT="gpt-4o-mini" \
        AZURE_AI_PROJECT_ENDPOINT="$AZURE_AI_PROJECT_ENDPOINT" \
        AZURE_TENANT_ID="$AZURE_TENANT_ID" \
        AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
        AZURE_CLIENT_SECRET="$AZURE_CLIENT_SECRET"

# Get the public IP and FQDN
az container show \
    --resource-group $RESOURCE_GROUP \
    --name cardiomedai-backend \
    --query ipAddress \
    --output table
```

## Step 7: Alternative - Deploy with Toolbox Sidecar

For a more complete deployment with the toolbox service:

```bash
# Create a deployment script
cat > deployment/deploy-with-toolbox.sh << 'EOF'
#!/bin/bash

# Set variables
RESOURCE_GROUP="cardiomedai-rg"
CONTAINER_GROUP_NAME="cardiomedai-full"
ACR_NAME="cardiomedaiacr"
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)

# Create container group with both containers
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_GROUP_NAME \
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
        TOOLBOX_URL="http://localhost:5000"

echo "Deployment completed!"
echo "API will be available at: http://cardiomedai-api.eastus.azurecontainer.io:8000"
EOF

chmod +x deployment/deploy-with-toolbox.sh
```

## Step 8: Verify Deployment

```bash
# Check container status
az container show \
    --resource-group $RESOURCE_GROUP \
    --name cardiomedai-backend \
    --query instanceView.state \
    --output tsv

# Get logs
az container logs \
    --resource-group $RESOURCE_GROUP \
    --name cardiomedai-backend

# Test the API
FQDN=$(az container show \
    --resource-group $RESOURCE_GROUP \
    --name cardiomedai-backend \
    --query ipAddress.fqdn \
    --output tsv)

curl http://$FQDN:8000/
```

## Step 9: Set Up Monitoring and Logging

```bash
# Create Log Analytics workspace
az monitor log-analytics workspace create \
    --resource-group $RESOURCE_GROUP \
    --workspace-name cardiomedai-logs \
    --location $LOCATION

# Get workspace ID and key
WORKSPACE_ID=$(az monitor log-analytics workspace show \
    --resource-group $RESOURCE_GROUP \
    --workspace-name cardiomedai-logs \
    --query customerId \
    --output tsv)

WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
    --resource-group $RESOURCE_GROUP \
    --workspace-name cardiomedai-logs \
    --query primarySharedKey \
    --output tsv)

# Update container with logging
az container create \
    --resource-group $RESOURCE_GROUP \
    --name cardiomedai-backend-monitored \
    --image $ACR_LOGIN_SERVER/cardiomedai-backend:latest \
    --cpu 1 \
    --memory 2 \
    --registry-login-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --dns-name-label cardiomedai-api \
    --ports 8000 \
    --log-analytics-workspace $WORKSPACE_ID \
    --log-analytics-workspace-key $WORKSPACE_KEY \
    --environment-variables \
        AZURE_API_KEY="$AZURE_API_KEY" \
        AZURE_ENDPOINT="$AZURE_ENDPOINT"
```

## Step 10: Production Considerations

### Security
```bash
# Use Azure Key Vault for secrets
az keyvault create \
    --name cardiomedai-kv \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION

# Store secrets
az keyvault secret set \
    --vault-name cardiomedai-kv \
    --name azure-api-key \
    --value "$AZURE_API_KEY"
```

### Scaling and High Availability
```bash
# For production, consider Azure Container Apps instead
az containerapp env create \
    --name cardiomedai-env \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION

az containerapp create \
    --name cardiomedai-app \
    --resource-group $RESOURCE_GROUP \
    --environment cardiomedai-env \
    --image $ACR_LOGIN_SERVER/cardiomedai-backend:latest \
    --target-port 8000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 10
```

## Troubleshooting

### Common Issues

1. **Container fails to start**
   ```bash
   az container logs --resource-group $RESOURCE_GROUP --name cardiomedai-backend
   ```

2. **Image pull errors**
   ```bash
   # Verify ACR credentials
   az acr credential show --name $ACR_NAME
   ```

3. **Network connectivity issues**
   ```bash
   # Check container IP and ports
   az container show --resource-group $RESOURCE_GROUP --name cardiomedai-backend --query ipAddress
   ```

### Cleanup

```bash
# Delete container instance
az container delete \
    --resource-group $RESOURCE_GROUP \
    --name cardiomedai-backend \
    --yes

# Delete resource group (removes everything)
az group delete --name $RESOURCE_GROUP --yes
```

## Cost Optimization

- Use **Azure Container Apps** for production workloads with auto-scaling
- Consider **Azure App Service** for simpler deployment
- Use **Azure Database for PostgreSQL** instead of SQLite for production
- Implement **Azure CDN** for static content delivery

Your CardioMed AI backend will be accessible at:
`http://cardiomedai-backend.eastus.azurecontainer.io:8000`