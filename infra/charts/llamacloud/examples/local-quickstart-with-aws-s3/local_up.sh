#!/bin/zsh
set -e

CURRENT_CONTEXT=$(kubectl config current-context)

if [ "$CURRENT_CONTEXT" != "docker-desktop" ]; then
  echo "Current kubectl context is $CURRENT_CONTEXT, not docker-desktop. Setting context to docker-desktop."
  kubectl config use-context docker-desktop
else
  echo "Current kubectl context is docker-desktop."
fi

echo "Installing dependencies..."

if helm status ingress-nginx -n ingress-nginx &> /dev/null; then
  echo "Release ingress-nginx exists."
else
echo "Installing ingress-nginx..."
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace
fi

if helm status postgresql &> /dev/null; then
  echo "Release postgresql exists."
else
  echo "Installing PostgreSQL..."
  helm upgrade --install postgresql oci://registry-1.docker.io/bitnamicharts/postgresql -f postgresql.yaml --wait --timeout 10m
fi

if helm status mongodb &> /dev/null; then
  echo "Release mongodb exists."
else
  echo "Installing MongoDB..."
  helm upgrade --install mongodb oci://registry-1.docker.io/bitnamicharts/mongodb -f mongodb.yaml --wait --timeout 10m
fi

if helm status redis &> /dev/null; then
  echo "Release redis exists."
else
  echo "Installing Redis..."
  helm upgrade --install redis oci://registry-1.docker.io/bitnamicharts/redis -f redis.yaml --wait --timeout 10m
fi

if helm status rabbitmq &> /dev/null; then
  echo "Release rabbitmq exists."
else
  echo "Installing RabbitMQ..."
  helm upgrade --install rabbitmq oci://registry-1.docker.io/bitnamicharts/rabbitmq -f rabbitmq.yaml --wait --timeout 10m
fi

if helm status temporal &> /dev/null; then
  echo "Release temporal exists."
else
  echo "Installing Temporal..."
  helm upgrade --install --repo https://go.temporal.io/helm-charts -f temporal.yaml temporal temporal --wait --timeout 10m
fi

echo "Installing LlamaIndex local chart..."
helm upgrade --install llamacloud ../../llamacloud -f values.yaml --wait --timeout 10m

echo "LlamaIndex local installation complete."
echo "Waiting for Ingress to be registered..."

sleep 10

echo "You can access the services via the following URLs: http://localhost"

open "http://localhost"