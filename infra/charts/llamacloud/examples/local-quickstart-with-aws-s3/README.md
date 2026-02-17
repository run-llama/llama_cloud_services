# LlamaCloud Local Quickstart with AWS S3

This example demonstrates how to deploy LlamaCloud locally using AWS S3 for storage. It provides a minimal configuration for quickly getting started with LlamaCloud on your local machine or development environment.

## Overview

This deployment configuration includes:
- Local infrastructure services (PostgreSQL, MongoDB, RabbitMQ, Redis, Temporal)
- AWS S3 for object storage (parsed documents, files, outputs)
- OIDC authentication support
- Optional LLM provider integrations
- Nginx ingress for local access

## Prerequisites

- Kubernetes cluster (local or remote)
- Helm 3.x installed
- AWS account with S3 bucket access
- LlamaCloud license key
- OIDC provider (e.g., Auth0, Okta, Google) for authentication
- Docker for Desktop with kubernetes enabled (set resources to max values in settings)

## Configuration Guide

The `values.yaml` file contains several configuration blocks that need to be customized for your deployment. Below is a comprehensive guide organized by section.

### Required Configuration Blocks

These sections contain `<REPLACE>` placeholders that **must** be filled in before deployment.

#### License Key (Required)

```yaml
license:
  key: "<REPLACE>"
```

**Instructions:**
- Replace `<REPLACE>` with your LlamaCloud license key
- Obtain a license key from [LlamaIndex](https://www.llamaindex.ai)

#### Authentication (Required)

```yaml
config:
  authentication:
    oidc:
      enabled: true
      discoveryUrl: "<REPLACE>"
      clientId: "<REPLACE>"
      clientSecret: "<REPLACE>"
```

**Instructions:**
- Replace `discoveryUrl` with your OIDC provider's discovery endpoint (e.g., `https://your-domain.auth0.com/.well-known/openid-configuration`)
- Replace `clientId` with your OIDC application/client ID
- Replace `clientSecret` with your OIDC application/client secret

#### Storage Buckets (Required)

```yaml
config:
  storageBuckets:
    provider: "aws"
    parsedDocuments: "<REPLACE>"
    parsedEtl: "<REPLACE>"
    parsedExternalComponents: "<REPLACE>"
    parsedFileParsing: "<REPLACE>"
    parsedRawFile: "<REPLACE>"
    parseOutput: "<REPLACE>"
    parsedFileScreenshot: "<REPLACE>"
    extractOutput: "<REPLACE>"
    parseFileUpload: "<REPLACE>"
    parseFileOutput: "<REPLACE>"
```

**Instructions:**
- Replace each `<REPLACE>` with your AWS S3 bucket names
- You can use the same bucket for all, or separate buckets for each purpose
- Example: `s3://my-llamacloud-bucket` or just `my-llamacloud-bucket`
- Ensure your AWS credentials have read/write access to these buckets

#### AWS Credentials (Required)

The following services require AWS credentials to access S3:

```yaml
backend:
  extraEnvVariables:
  - name: AWS_ACCESS_KEY_ID
    value: "<REPLACE>"
  - name: AWS_SECRET_ACCESS_KEY
    value: "<REPLACE>"

jobsService:
  extraEnvVariables:
  - name: AWS_ACCESS_KEY_ID
    value: "<REPLACE>"
  - name: AWS_SECRET_ACCESS_KEY
    value: "<REPLACE>"

jobsWorker:
  extraEnvVariables:
  - name: AWS_ACCESS_KEY_ID
    value: "<REPLACE>"
  - name: AWS_SECRET_ACCESS_KEY
    value: "<REPLACE>"

llamaParse:
  extraEnvVariables:
  - name: AWS_ACCESS_KEY_ID
    value: "<REPLACE>"
  - name: AWS_SECRET_ACCESS_KEY
    value: "<REPLACE>"

llamaParseOcr:
  extraEnvVariables:
  - name: AWS_ACCESS_KEY_ID
    value: "<REPLACE>"
  - name: AWS_SECRET_ACCESS_KEY
    value: "<REPLACE>"

llamaParseLayoutDetectionApi:
  extraEnvVariables:
  - name: AWS_ACCESS_KEY_ID
    value: "<REPLACE>"
  - name: AWS_SECRET_ACCESS_KEY
    value: "<REPLACE>"

temporalWorkloads:
  llamaParse:
    extraEnvVariables:
    - name: AWS_ACCESS_KEY_ID
      value: "<REPLACE>"
    - name: AWS_SECRET_ACCESS_KEY
      value: "<REPLACE>"

  jobsService:
    extraEnvVariables:
    - name: AWS_ACCESS_KEY_ID
      value: "<REPLACE>"
    - name: AWS_SECRET_ACCESS_KEY
      value: "<REPLACE>"

  workers:
    temporal-jobs-worker:
      extraEnvVariables:
      - name: AWS_ACCESS_KEY_ID
        value: "<REPLACE>"
      - name: AWS_SECRET_ACCESS_KEY
        value: "<REPLACE>"
```

**Instructions:**
- Replace all AWS credential placeholders with your AWS access key ID and secret access key
- Ensure the IAM user/role has appropriate S3 permissions
- **Security Warning:** For production deployments, use Kubernetes secrets or a secret management solution instead of hardcoded credentials

### Optional Configuration Blocks

These sections contain `<REPLACE_OR_REMOVE>` placeholders. These blocks are **entirely optional** and can be removed if you don't plan to use them.

#### OpenAI (Optional)

```yaml
config:
  llms:
    openAi:
      apiKey: "<REPLACE_OR_REMOVE>"
```

**Instructions:**
- **Optional:** This block can be completely removed if you don't plan to use OpenAI models
- If using OpenAI, replace with your OpenAI API key from [platform.openai.com](https://platform.openai.com)

#### Anthropic (Optional)

```yaml
config:
  llms:
    anthropic:
      apiKey: "<REPLACE_OR_REMOVE>"
```

**Instructions:**
- **Optional:** This block can be completely removed if you don't plan to use Anthropic models
- If using Anthropic, replace with your Anthropic API key from [console.anthropic.com](https://console.anthropic.com)

#### Google Gemini (Optional)

```yaml
config:
  llms:
    gemini:
      apiKey: "<REPLACE_OR_REMOVE>"
```

**Instructions:**
- **Optional:** This block can be completely removed if you don't plan to use Google Gemini models
- If using Gemini, replace with your Google AI API key from [makersuite.google.com](https://makersuite.google.com)

#### Azure OpenAI (Optional)

```yaml
config:
  llms:
    azureOpenAi:
      deployments:
      - model: "gpt-4.1"
        deploymentName: "gpt-4.1"
        apiKey: "<REPLACE_OR_REMOVE>"
        baseUrl: "<REPLACE_OR_REMOVE>"
        apiVersion: "2024-12-01-preview"
      # ... additional deployments
```

**Instructions:**
- **Optional:** This entire `azureOpenAi` section can be removed if you're not using Azure OpenAI
- If using Azure OpenAI, for each deployment you want to use:
  - Replace `apiKey` with your Azure OpenAI API key
  - Replace `baseUrl` with your Azure OpenAI endpoint (e.g., `https://your-resource.openai.azure.com`)
  - Remove unused deployment configurations
  - Update model names to match your Azure deployments

#### AWS Bedrock (Optional)

```yaml
config:
  llms:
    awsBedrock:
      region: "<REPLACE_OR_REMOVE>"
      accessKeyId: "<REPLACE_OR_REMOVE>"
      secretAccessKey: "<REPLACE_OR_REMOVE>"
      sonnet3_5ModelVersionName: "anthropic.claude-3-5-sonnet-20240620-v1:0"
      # ... additional model configurations
```

**Instructions:**
- **Optional:** This entire `awsBedrock` section can be removed if you're not using AWS Bedrock
- If using AWS Bedrock:
  - Replace `region` with your AWS region (e.g., `us-east-1`)
  - Replace `accessKeyId` with your AWS access key ID
  - Replace `secretAccessKey` with your AWS secret access key
  - Adjust model version names as needed for your Bedrock configuration

#### Google Vertex AI (Optional)

```yaml
config:
  llms:
    googleVertexAi:
      projectId: "<REPLACE_OR_REMOVE>"
      location: "<REPLACE_OR_REMOVE>"
      credentialsJson: '<REPLACE_OR_REMOVE>'
```

**Instructions:**
- **Optional:** This entire `googleVertexAi` section can be removed if you're not using Google Vertex AI
- If using Vertex AI:
  - Replace `projectId` with your Google Cloud project ID
  - Replace `location` with your preferred region (e.g., `us-central1`)
  - Replace `credentialsJson` with your service account JSON key (properly escaped)

### Pre-configured Infrastructure Services

The following services are pre-configured for local development and typically don't require changes:

#### PostgreSQL
```yaml
postgresql:
  host: "postgresql"
  port: "5432"
  database: "llamacloud"
  username: "llamacloud"
  password: "llamacloud"
```

#### MongoDB
```yaml
mongodb:
  scheme: "mongodb"
  host: "mongodb"
  port: "27017"
  username: "root"
  password: "password"
```

#### RabbitMQ
```yaml
rabbitmq:
  scheme: "amqp"
  host: "rabbitmq"
  port: "5672"
  username: "admin"
  password: "password"
```

#### Redis
```yaml
redis:
  host: "redis-master"
  port: "6379"
  scheme: "redis"
  password: "password"
```

#### Temporal
```yaml
temporal:
  enabled: true
  host: "temporal-frontend"
  port: 7233
```

### Ingress Configuration

```yaml
ingress:
  enabled: true
  host: "localhost"
  ingressClassName: "nginx"
```

**Instructions:**

## Deployment Instructions

### Step 1: Prepare Configuration

1. Edit `values.yaml` and replace all required `<REPLACE>` placeholders

3. Remove or configure optional `<REPLACE_OR_REMOVE>` blocks based on your needs

### Step 2: Deploy LlamaCloud

```bash
# Deploy llamacloud with the supporting helm charts
./local_up.sh
```

### Step 3: Verify Deployment

```bash
# Check pod status
kubectl get pods

# Check ingress
kubectl get ingress

# View logs
kubectl logs -l app=llamacloud-backend
```

### Step 4: Access LlamaCloud

Access the application:
```
http://localhost
```

## Troubleshooting

### Common Issues

**Pods not starting:**
- Check logs: `kubectl logs <pod-name>`
- Verify all required services are running
- Ensure AWS credentials are correct and have S3 permissions

**Authentication errors:**
- Verify OIDC configuration is correct
- Check that the discovery URL is accessible
- Ensure client ID and secret match your OIDC provider

**S3 access errors:**
- Verify AWS credentials have proper IAM permissions
- Check that bucket names are correct and exist
- Ensure buckets are in the correct region

**Connection errors to infrastructure services:**
- Verify all infrastructure services (PostgreSQL, MongoDB, etc.) are running
- Check service names and ports match your deployment
- Review network policies if using network restrictions

## Security Considerations

For production deployments:

1. **Use Kubernetes Secrets** for sensitive data instead of plain text values
2. **Enable TLS** for ingress with valid certificates
3. **Use IAM roles** (e.g., IRSA on EKS) instead of hardcoded AWS credentials
4. **Change default passwords** for all infrastructure services
5. **Enable network policies** to restrict pod-to-pod communication
6. **Use a secrets management solution** (e.g., HashiCorp Vault, AWS Secrets Manager)

## Next Steps

- Configure additional LLM providers as needed
- Set up monitoring and observability
- Review and adjust resource limits for production workloads
- Enable additional features (OCR, layout detection)
- Review the [LlamaCloud documentation](https://docs.llamaindex.ai) for advanced configuration options

## Support

For issues and questions:
- Review the main [LlamaCloud documentation](https://docs.llamaindex.ai)
- Contact LlamaIndex support with your license information
