# CardioMed AI Azure Deployment

This directory contains all the necessary files and scripts to deploy the CardioMed AI backend to Azure Container Instances.

## Quick Start

1. **Set up environment variables:**
   ```bash
   export AZURE_API_KEY="your_azure_api_key"
   export AZURE_ENDPOINT="your_azure_endpoint"
   export AZURE_AI_PROJECT_ENDPOINT="your_azure_ai_project_endpoint"
   export AZURE_TENANT_ID="your_tenant_id"
   export AZURE_CLIENT_ID="your_client_id"
   export AZURE_CLIENT_SECRET="your_client_secret"
   ```

2. **Run the deployment script:**
   ```bash
   chmod +x deployment/deploy.sh
   ./deployment/deploy.sh
   ```

3. **Access your API:**
   The script will output the URL where your API is accessible.

## Files

- `Dockerfile.production` - Production-ready Docker configuration
- `.env.production` - Template for production environment variables
- `deploy.sh` - Automated deployment script
- `azure-deployment.md` - Detailed deployment guide

## Manual Deployment

If you prefer manual deployment, follow the detailed guide in `azure-deployment.md`.

## Cost Considerations

- Azure Container Instances pricing is based on CPU, memory, and duration
- Estimated cost: ~$30-50/month for basic usage
- Consider Azure Container Apps for production workloads with auto-scaling

## Security Notes

- All sensitive environment variables are passed securely
- Container runs as non-root user
- Health checks are configured
- Consider using Azure Key Vault for production secrets

## Monitoring

After deployment, you can monitor your application using:

```bash
# View logs
az container logs --resource-group cardiomedai-rg --name cardiomedai-backend

# Check status
az container show --resource-group cardiomedai-rg --name cardiomedai-backend --query instanceView.state

# Get metrics
az monitor metrics list --resource /subscriptions/{subscription-id}/resourceGroups/cardiomedai-rg/providers/Microsoft.ContainerInstance/containerGroups/cardiomedai-backend
```