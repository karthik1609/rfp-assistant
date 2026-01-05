# Azure Container Apps Deployment

This guide walks you through deploying the RFP Assistant to Azure Container Apps.

## Overview

Azure Container Apps supports docker-compose files natively, making it the ideal choice for this multi-container application.

## Step 1: Prerequisites Setup

### 1.1 Create Resource Group

```bash
RESOURCE_GROUP="rg-rfp-assistant"
LOCATION="westeurope"  # or your preferred region

az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### 1.2 Create Azure Container Registry (ACR)

```bash
ACR_NAME="rfpassistant$(openssl rand -hex 3)"  # Must be globally unique

az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true
```

### 1.3 Create Storage Account (if not exists)

```bash
STORAGE_ACCOUNT="rfpassistant$(openssl rand -hex 3)"  # Must be globally unique

az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --sku Standard_LRS

# Get connection string
az storage account show-connection-string \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --query connectionString \
  --output tsv
```

Save the connection string - you'll need it for environment variables.

### 1.4 Create Container Apps Environment

```bash
ENV_NAME="rfp-assistant-env"

az containerapp env create \
  --name $ENV_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

## Step 2: Build and Push Docker Images

### 2.1 Login to ACR

```bash
az acr login --name $ACR_NAME
```

### 2.2 Build and Push Images

From the project root directory:

```bash
# Build and push backend
docker build -f backend.Dockerfile -t $ACR_NAME.azurecr.io/rfp-backend:latest .
docker push $ACR_NAME.azurecr.io/rfp-backend:latest

# Build and push frontend
docker build -f frontend.Dockerfile -t $ACR_NAME.azurecr.io/rfp-frontend:latest .
docker push $ACR_NAME.azurecr.io/rfp-frontend:latest
```

## Step 3: Create Container Apps

### 3.1 Create Backend Container App

```bash
BACKEND_APP_NAME="rfp-backend"

az containerapp create \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR_NAME.azurecr.io/rfp-backend:latest \
  --target-port 8001 \
  --ingress external \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_NAME \
  --registry-password $(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv) \
  --env-vars \
    "HF_TOKEN=your-hf-token" \
    "AZURE_OPENAI_API_KEY=your-key" \
    "AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/" \
    "AZURE_OPENAI_API_VERSION=2024-02-15-preview" \
    "AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-chat" \
    "AZURE_OPENAI_EMBEDDING_API_KEY=your-key" \
    "AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-resource.openai.azure.com/" \
    "AZURE_OPENAI_EMBEDDING_API_VERSION=2024-02-15-preview" \
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-large" \
    "AZURE_STORAGE_CONNECTION_STRING=your-connection-string" \
  --cpu 2 \
  --memory 4Gi \
  --min-replicas 1 \
  --max-replicas 1
```

### 3.2 Create Frontend Container App

```bash
FRONTEND_APP_NAME="rfp-frontend"

# Get backend URL
BACKEND_URL=$(az containerapp show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.configuration.ingress.fqdn" -o tsv)

az containerapp create \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image $ACR_NAME.azurecr.io/rfp-frontend:latest \
  --target-port 80 \
  --ingress external \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_NAME \
  --registry-password $(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv) \
  --env-vars "VITE_API_URL=https://$BACKEND_URL" \
  --cpu 0.5 \
  --memory 1Gi \
  --min-replicas 1 \
  --max-replicas 1
```

**Note**: The frontend needs to be rebuilt with the correct API URL. See "Frontend Configuration" below.

## Step 4: Frontend Configuration

The frontend needs the backend URL at build time. You have two options:

### Option A: Rebuild with Environment Variable (Recommended)

1. Update `docker-compose.yml` or create a `.env.production` file:
   ```bash
   VITE_API_URL=https://rfp-backend.your-env.azurecontainerapps.io
   ```

2. Rebuild and push:
   ```bash
   docker build -f frontend.Dockerfile -t $ACR_NAME.azurecr.io/rfp-frontend:latest .
   docker push $ACR_NAME.azurecr.io/rfp-frontend:latest
   ```

3. Update the container app:
   ```bash
   az containerapp update \
     --name $FRONTEND_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --image $ACR_NAME.azurecr.io/rfp-frontend:latest
   ```

### Option B: Use Runtime Configuration (Advanced)

Modify the frontend to read the API URL from a config file that's injected at runtime.

## Step 5: Access Your Application

Get the frontend URL:

```bash
az containerapp show \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

Your application will be available at: `https://rfp-frontend.your-env.azurecontainerapps.io`

## Step 6: Persistent Storage

For persistent storage of output files, you have two options:

### Option A: Azure Files (Recommended for Container Apps)

```bash
# Create Azure File Share
STORAGE_KEY=$(az storage account keys list \
  --resource-group $RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT \
  --query "[0].value" -o tsv)

az storage share create \
  --name rfp-outputs \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY

# Mount to backend container app
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars "STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT" "STORAGE_ACCOUNT_KEY=$STORAGE_KEY" \
  --volume-name rfp-storage \
  --storage-name rfp-storage \
  --storage-type AzureFile \
  --storage-account $STORAGE_ACCOUNT \
  --storage-share-name rfp-outputs \
  --mount-path /app/output
```

### Option B: Azure Blob Storage (Current Implementation)

The application already uses Azure Blob Storage for RAG indexes. Output files can also be stored in blob storage by modifying the application to upload generated documents.

## Updating the Application

To update after making changes:

```bash
# Rebuild and push images
docker build -f backend.Dockerfile -t $ACR_NAME.azurecr.io/rfp-backend:latest .
docker push $ACR_NAME.azurecr.io/rfp-backend:latest

docker build -f frontend.Dockerfile -t $ACR_NAME.azurecr.io/rfp-frontend:latest .
docker push $ACR_NAME.azurecr.io/rfp-frontend:latest

# Update container apps
az containerapp update \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/rfp-backend:latest

az containerapp update \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/rfp-frontend:latest
```

## Cost Optimization

- **Min replicas = 1**: Keeps the app always running (required for your use case)
- **CPU/Memory**: Adjust based on usage. Start with 2 CPU / 4Gi for backend, 0.5 CPU / 1Gi for frontend
- **Monitoring**: Use Azure Monitor to track costs and optimize

## Troubleshooting

### View Logs

```bash
# Backend logs
az containerapp logs show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow

# Frontend logs
az containerapp logs show \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow
```

### Check Container Status

```bash
az containerapp show \
  --name $BACKEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "properties.runningStatus"
```

## Automated Deployment Script

See `deploy.sh` for an automated deployment script that handles all these steps.

