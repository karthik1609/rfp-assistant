RESOURCE_GROUP="general_dev"
LOCATION="centralindia"
ENV_NAME="general_dev_env"
ACE_NAME="fxdevacr"

HF_TOKEN=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=
AZURE_OPENAI_DEPLOYMENT_NAME=
AZURE_OPENAI_EMBEDDING_API_KEY=
AZURE_OPENAI_EMBEDDING_ENDPOINT=
AZURE_OPENAI_EMBEDDING_API_VERSION=
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=
AZURE_STORAGE_CONNECTION_STRING=

#login to acr
az acr login --name $ACR_NAME

#build and push images
docker build -f backend.Dockerfile -t $ACR_NAME.azurecr.io/rfp-backend:latest .
docker push $ACR_NAME.azurecr.io/rfp-backend:latest

docker build -f frontend.Dockerfile -t $ACR_NAME.azurecr.io/rfp-frontend:latest .
docker push $ACR_NAME.azurecr.io/rfp-frontend:latest

#create backend container app
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
        "HF_TOKEN=$HF_TOKEN" \
        "AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY" \
        "AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
        "AZURE_OPENAI_API_VERSION=$AZURE_OPENAI_API_VERSION" \
        "AZURE_OPENAI_DEPLOYMENT_NAME=$AZURE_OPENAI_DEPLOYMENT_NAME" \
        "AZURE_OPENAI_EMBEDDING_API_KEY=$AZURE_OPENAI_EMBEDDING_API_KEY" \
        "AZURE_OPENAI_EMBEDDING_ENDPOINT=$AZURE_OPENAI_EMBEDDING_ENDPOINT" \
        "AZURE_OPENAI_EMBEDDING_API_VERSION=$AZURE_OPENAI_EMBEDDING_API_VERSION" \
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=$AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME" \
        "AZURE_STORAGE_CONNECTION_STRING=$AZURE_STORAGE_CONNECTION_STRING" \
    --cpu 2 \
    --memory 4Gi \
    --min-replicas 1 \
    --max-replicas 1

#create frontend container app
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

  
  #frontend config

  #update docker-compose.yml
  VITE_API_URL=https://rfp-backend.your-env.azurecontainerapps.io

  #rebuild and push 
  docker build -f frontend.Dockerfile -t $ACR_NAME.azurecr.io/rfp-frontend:latest .
  docker push $ACR_NAME.azurecr.io/rfp-frontend:latest

  #update container app
  az containerapp update \
    --name $FRONTEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --image $ACR_NAME.azurecr.io/rfp-frontend:latest