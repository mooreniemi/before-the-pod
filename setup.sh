#!/bin/bash
set -euo pipefail

echo "🧱 Starting Minikube with Docker driver..."
minikube start --driver=docker

echo "🔁 Pointing shell to Minikube's Docker daemon..."
eval $(minikube docker-env)

echo "🔐 Generating TLS cert with SAN..."
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout deploy/certs/tls.key \
  -out deploy/certs/tls.crt \
  -config openssl.cnf \
  -extensions v3_req

echo "🔐 Creating Kubernetes TLS secret..."
kubectl delete secret before-the-pod-tls --ignore-not-found
kubectl create secret tls before-the-pod-tls \
  --cert=deploy/certs/tls.crt \
  --key=deploy/certs/tls.key

echo "🧪 Base64 encoding cert for webhook config..."
CA_BUNDLE=$(base64 < deploy/certs/tls.crt | tr -d '\n')

echo "📄 Injecting caBundle into webhook.yaml..."
sed "s|caBundle: .*|caBundle: ${CA_BUNDLE}|" deploy/webhook.yaml > deploy/webhook.generated.yaml

echo "🐳 Building mlflow test image (with-mlflow:latest)..."
docker build -t with-mlflow:latest - <<EOF
FROM python:3.11-slim
RUN pip install mlflow
CMD ["python"]
EOF

echo "🐳 Building webhook server image (before-the-pod:latest)..."
docker build -t before-the-pod:latest -f server/Dockerfile .

echo "🚀 Deploying webhook server & service..."
kubectl apply -f deploy/k8s-deployment.yaml

echo "🧠 Registering ValidatingWebhookConfiguration..."
kubectl apply -f deploy/webhook.generated.yaml

echo "✅ Setup complete. You can now run:"
echo "  kubectl apply -f deploy/job-good.yaml"
echo "  kubectl apply -f deploy/job-bad.yaml"
