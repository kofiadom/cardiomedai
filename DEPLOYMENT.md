# CardioMed AI Deployment Guide

This guide explains how to run CardioMed AI in both local development and Docker production modes.

## Prerequisites

- Docker and Docker Compose installed
- Azure SQL Database configured and accessible
- All environment variables set in `.env` file

## Local Development Mode

### 1. Switch to Local Mode
```powershell
.\switch-mode.ps1 local
```

### 2. Start MCP Toolbox
```bash
docker run --rm -p 5000:5000 \
  -v "./app/advisor_agent/tools.yaml:/tools.yaml" \
  us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:0.7.0 \
  /toolbox --tools-file /tools.yaml --address 0.0.0.0 --port 5000
```

### 3. Start FastAPI Application
```bash
uv run app/main.py
```

### 4. Access Application
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## Docker Production Mode

### 1. Configure Environment Variables
Ensure your `.env` file contains all required variables (see Environment Variables section below).

### 2. Switch to Docker Mode
```powershell
.\switch-mode.ps1 docker
```

### 3. Build and Run with Docker Compose
```bash
docker-compose up --build
```

### 3. Access Application
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## Environment Variables

### Required Variables
- `AZURE_API_KEY` - Azure OpenAI API key
- `AZURE_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_AI_PROJECT_ENDPOINT` - Azure AI Foundry project endpoint
- `HEALTH_ADVISOR_AGENT_ID` - Health advisor agent ID
- `KNOWLEDGE_AGENT_ID` - Knowledge agent ID
- `DATABASE_URL` - Azure SQL Database connection string

### Mode-Specific Variables
- **Local**: `TOOLBOX_URL="http://localhost:5000"`
- **Docker**: `TOOLBOX_URL="http://toolbox:5000"`

## Troubleshooting

### Common Issues

1. **"Cannot connect to toolbox"**
   - Ensure MCP Toolbox is running
   - Check TOOLBOX_URL matches your deployment mode

2. **"Incorrect syntax near 'LIMIT'"**
   - Ensure tools.yaml uses SQL Server syntax (TOP instead of LIMIT)

3. **Database connection issues**
   - Verify Azure SQL Database firewall allows your IP
   - Check DATABASE_URL format and credentials

### Health Checks

- **MCP Toolbox**: http://localhost:5000/health (if available)
- **FastAPI**: http://localhost:8000/docs
- **Database**: Test with any API endpoint that queries data

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │───▶│   MCP Toolbox   │───▶│  Azure SQL DB   │
│  (port 8000)    │    │  (port 5000)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Render Deployment

### MCP Toolbox on Render

The `Dockerfile-toolbox` is configured for secure deployment on Render using environment variable substitution.

**Required Environment Variables for Render MCP Toolbox:**
```
DB_HOST=cardiomed-ai-db-server.database.windows.net
DB_NAME=cardiomed-ai-db
DB_USER=harold
DB_PASSWORD=realControlissurgical@911
```

**Note:** These exact variable names (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) must be used as they match the placeholders in `tools.yaml`.

**How it works:**
1. The Dockerfile copies `tools.yaml` as a template
2. At runtime, `envsubst` replaces `${DB_HOST}`, `${DB_NAME}`, etc. with actual values
3. The toolbox starts with the processed configuration
4. **No credentials are stored in the Docker image or Git repository**

### FastAPI Backend on Render

Set the same environment variables plus:
```
AZURE_API_KEY=your_azure_api_key
AZURE_ENDPOINT=your_azure_endpoint
AZURE_AI_PROJECT_ENDPOINT=your_project_endpoint
HEALTH_ADVISOR_AGENT_ID=your_agent_id
KNOWLEDGE_AGENT_ID=your_knowledge_agent_id
TOOLBOX_URL=https://your-toolbox-service.onrender.com
```

## Production Considerations

1. **Security**: Use Azure Key Vault for secrets in production
2. **Scaling**: Consider Azure Container Instances or AKS
3. **Monitoring**: Add health checks and logging
4. **Backup**: Ensure Azure SQL Database backup is configured
5. **Environment Variables**: Never commit credentials to Git - always use environment variables
