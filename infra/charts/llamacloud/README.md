# LlamaCloud Helm Chart

The Helm Chart for installing LlamaCloud in Kubernetes. Deplying Self-Hosted LlamaCloud on your own infrastructure enables you to build data-intensive AI applications in your own [virtual](https://aws.amazon.com/vpc/) [private](https://azure.microsoft.com/en-us/free/hybrid-cloud/search/) [cloud](https://cloud.google.com/vpc?hl=en) while meeting your data privacy and compliance requirements.

## Quick Start

```sh
# Add the LlamaIndex Helm Chart Repository
helm repo add llamaindex https://run-llama.github.io/helm-charts

# (Optional) Update repo information
helm repo update

# Install the basic version of the chart
helm install my-llamacloud-release llamaindex/llamacloud
```

## Prerequisites

- Kubernetes `>=1.28.0`
    - We are largely aligned with the versions supported in [EKS](https://endoflife.date/amazon-eks), [AKS](https://learn.microsoft.com/en-us/azure/aks/supported-kubernetes-versions?tabs=azure-cli), and [GKE](https://cloud.google.com/kubernetes-engine/versioning).
- Helm v3.7.0+ [(Docs)](https://helm.sh/docs/)
- LlamaCloud Images - [(Docker Hub Repository)](https://hub.docker.com/u/llamaindex)
    - By default, this chart uses public images for all LlamaCloud specific services and its dependencies.
- LlamaCloud License Key

## Hardware Requirements

- **Linux Instances running x86 cpus**
    - As of August 12th, 2024, we build only linux/amd64 images. arm64 is not supported at this moment.
- **Ubuntu >=22.04**
- **>=12 vCPUs**
- **>=80Gbi Memory**

Warning #1: LlamaParse, LlamaIndex's proprietry document parser, can be a very resource intensive deployment to run, especially if you want to maximize performance.
Warning #2:The base cpu/memory requirements may increase if you are running containerized deployments of LlamaCloud dependencies. (More information in the following section)

## Configuring Dependencies

The LlamaCloud charts provide easy deployment options for the 3rd party dependencies that the platform requires. Each of the following dependencies can be enabled directly through the `values.yaml` file, or alternatively, you can supply your own `Secret` objects to provide the LlamaCloud deployments with the necessar credentials to those services.

- S3Proxy (Templates)
    - If enabled, we are deploying a containerized version of gaul's [s3proxy project](https://github.com/gaul/s3proxy).
    - If you wish to use a non-aws file store such as Azure Blob Storage or GCP Filestore, enable and configure the s3proxy deployment. For more information, please refer to our docs.

## Documentation

We provide a couple of guides directly in the `docs` directory of this repository.

- [Monitoring](./docs/monitoring/README.md)
- [S3Proxy Setup](./docs/s3-proxy-setup.md)

For more information about using this chart, visit the [Official LlamaCloud Documentation](https://llamaindex.ai).

## Parameters

### License Configuration

| Name             | Description                                       | Value                      |
| ---------------- | ------------------------------------------------- | -------------------------- |
| `license.key`    | License key for all components                    | `<input-license-key-here>` |
| `license.secret` | Name of the k8s secret to use for the license key | `""`                       |

### Postgresql Configuration

| Name                  | Description                                                   | Value  |
| --------------------- | ------------------------------------------------------------- | ------ |
| `postgresql.host`     | PostgreSQL host                                               | `""`   |
| `postgresql.port`     | PostgreSQL port                                               | `5432` |
| `postgresql.database` | PostgreSQL database                                           | `""`   |
| `postgresql.username` | PostgreSQL user                                               | `""`   |
| `postgresql.password` | PostgreSQL password                                           | `""`   |
| `postgresql.secret`   | Name of the existing secret to use for PostgreSQL credentials | `""`   |

### MongoDB Configuration

| Name                  | Description                                                | Value     |
| --------------------- | ---------------------------------------------------------- | --------- |
| `mongodb.scheme`      | MongoDB connection scheme (i.e. mongodb, mongodb+srv)      | `mongodb` |
| `mongodb.host`        | MongoDB host                                               | `""`      |
| `mongodb.port`        | MongoDB port                                               | `27017`   |
| `mongodb.username`    | MongoDB user                                               | `""`      |
| `mongodb.password`    | MongoDB password                                           | `""`      |
| `mongodb.mongodb_url` | Full MongoDB connection URL                                | `""`      |
| `mongodb.secret`      | Name of the existing secret to use for MongoDB credentials | `""`      |

### RabbitMQ Configuration

| Name                        | Description                                                        | Value  |
| --------------------------- | ------------------------------------------------------------------ | ------ |
| `rabbitmq.scheme`           | RabbitMQ scheme                                                    | `amqp` |
| `rabbitmq.host`             | RabbitMQ host                                                      | `""`   |
| `rabbitmq.port`             | RabbitMQ port                                                      | `5672` |
| `rabbitmq.username`         | RabbitMQ user                                                      | `""`   |
| `rabbitmq.password`         | RabbitMQ password                                                  | `""`   |
| `rabbitmq.connectionString` | Connection string for the AMQP queue (e.g., for Azure Service Bus) | `""`   |
| `rabbitmq.secret`           | Name of the existing secret to use for RabbitMQ credentials        | `""`   |

### Redis Configuration

| Name             | Description                                              | Value   |
| ---------------- | -------------------------------------------------------- | ------- |
| `redis.host`     | Redis host                                               | `""`    |
| `redis.port`     | Redis port                                               | `6379`  |
| `redis.scheme`   | Redis connection scheme (redis or rediss for SSL)        | `redis` |
| `redis.username` | Redis username (required for Redis 6.0+)                 | `""`    |
| `redis.password` | Redis password                                           | `""`    |
| `redis.db`       | Redis database                                           | `0`     |
| `redis.secret`   | Name of the existing secret to use for Redis credentials | `""`    |

### Optional QDRANT Data-Sink configuration

| Name             | Description                                                 | Value   |
| ---------------- | ----------------------------------------------------------- | ------- |
| `qdrant.enabled` | Enable QDRANT Data-Sink for backend                         | `false` |
| `qdrant.url`     | QDRANT Data-Sink host                                       | `""`    |
| `qdrant.apiKey`  | QDRANT Data-Sink API key                                    | `""`    |
| `qdrant.secret`  | Name of the existing secret to use for the QDRANT Data-Sink | `""`    |

### Temporal configuration (required) - either deploy Temporal as a subchart or connect to an external Temporal instance

| Name                | Description                                                                        | Value   |
| ------------------- | ---------------------------------------------------------------------------------- | ------- |
| `temporal.disabled` | Completely disable Temporal and all Temporal workloads (configmaps, jobs, workers) | `false` |
| `temporal.deploy`   | Deploy Temporal as a subchart (if false, use external Temporal)                    | `false` |
| `temporal.host`     | Temporal host (ignored when deploy is true, auto-configured to subchart)           | `""`    |
| `temporal.port`     | Temporal port (ignored when deploy is true, auto-configured to subchart)           | `7233`  |

### Temporal Subchart Configuration

| Name                                                                         | Description                                                              | Value                        |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ---------------------------- |
| `temporal-subchart.serviceAccount.create`                                    | Create a service account for Temporal                                    | `true`                       |
| `temporal-subchart.serviceAccount.name`                                      | Name of the service account for Temporal                                 | `temporal-server`            |
| `temporal-subchart.web.enabled`                                              | Enable Temporal Web UI                                                   | `true`                       |
| `temporal-subchart.web.service.port`                                         | Port for Temporal Web UI service                                         | `80`                         |
| `temporal-subchart.server.config.persistence.default.driver`                 | Persistence driver for default store                                     | `sql`                        |
| `temporal-subchart.server.config.persistence.default.sql.driver`             | SQL driver for default store                                             | `postgres12`                 |
| `temporal-subchart.server.config.persistence.default.sql.host`               | PostgreSQL host (use same as postgresql.host)                            | `""`                         |
| `temporal-subchart.server.config.persistence.default.sql.port`               | PostgreSQL port (use same as postgresql.port)                            | `5432`                       |
| `temporal-subchart.server.config.persistence.default.sql.database`           | Database name for temporal (created automatically)                       | `temporal`                   |
| `temporal-subchart.server.config.persistence.default.sql.user`               | PostgreSQL user (use same as postgresql.username)                        | `""`                         |
| `temporal-subchart.server.config.persistence.default.sql.existingSecret`     | Use existing secret for password (auto-created from postgresql.password) | `temporal-postgresql-secret` |
| `temporal-subchart.server.config.persistence.default.sql.maxConns`           | Maximum number of connections for default store                          | `20`                         |
| `temporal-subchart.server.config.persistence.default.sql.maxIdleConns`       | Maximum number of idle connections for default store                     | `20`                         |
| `temporal-subchart.server.config.persistence.default.sql.maxConnLifetime`    | Maximum connection lifetime for default store                            | `1h`                         |
| `temporal-subchart.server.config.persistence.visibility.driver`              | Persistence driver for visibility store                                  | `sql`                        |
| `temporal-subchart.server.config.persistence.visibility.sql.driver`          | SQL driver for visibility store                                          | `postgres12`                 |
| `temporal-subchart.server.config.persistence.visibility.sql.host`            | PostgreSQL host (use same as postgresql.host)                            | `""`                         |
| `temporal-subchart.server.config.persistence.visibility.sql.port`            | PostgreSQL port (use same as postgresql.port)                            | `5432`                       |
| `temporal-subchart.server.config.persistence.visibility.sql.database`        | Database name for temporal visibility (created automatically)            | `temporal_visibility`        |
| `temporal-subchart.server.config.persistence.visibility.sql.user`            | PostgreSQL user (use same as postgresql.username)                        | `""`                         |
| `temporal-subchart.server.config.persistence.visibility.sql.existingSecret`  | Use existing secret for password (auto-created from postgresql.password) | `temporal-postgresql-secret` |
| `temporal-subchart.server.config.persistence.visibility.sql.maxConns`        | Maximum number of connections for visibility store                       | `20`                         |
| `temporal-subchart.server.config.persistence.visibility.sql.maxIdleConns`    | Maximum number of idle connections for visibility store                  | `20`                         |
| `temporal-subchart.server.config.persistence.visibility.sql.maxConnLifetime` | Maximum connection lifetime for visibility store                         | `1h`                         |
| `temporal-subchart.schema.createDatabase.enabled`                            | Enable automatic database creation for Temporal                          | `true`                       |
| `temporal-subchart.schema.setup.enabled`                                     | Enable schema setup for Temporal                                         | `true`                       |
| `temporal-subchart.schema.update.enabled`                                    | Enable schema updates for Temporal                                       | `true`                       |
| `temporal-subchart.prometheus.enabled`                                       | Enable Prometheus for Temporal (disabled, use main monitoring)           | `false`                      |
| `temporal-subchart.grafana.enabled`                                          | Enable Grafana for Temporal (disabled, use main monitoring)              | `false`                      |
| `temporal-subchart.elasticsearch.enabled`                                    | Enable Elasticsearch for Temporal                                        | `false`                      |
| `temporal-subchart.cassandra.enabled`                                        | Enable Cassandra for Temporal                                            | `false`                      |
| `temporal-subchart.mysql.enabled`                                            | Enable MySQL for Temporal                                                | `false`                      |
| `temporal-subchart.postgresql.enabled`                                       | Enable bundled PostgreSQL for Temporal (disabled, use external)          | `false`                      |

### Ingress Configuration

| Name                       | Description                               | Value   |
| -------------------------- | ----------------------------------------- | ------- |
| `ingress.enabled`          | Whether to enable the ingress             | `false` |
| `ingress.annotations`      | Annotations to add to the ingress         | `{}`    |
| `ingress.host`             | Hostname to use for the ingress           | `""`    |
| `ingress.tlsSecretName`    | TLS secret name to use for the ingress    | `""`    |
| `ingress.ingressClassName` | Ingress class name to use for the ingress | `""`    |

### Application Configuration

| Name              | Description                                                           | Value  |
| ----------------- | --------------------------------------------------------------------- | ------ |
| `config.logLevel` | Log level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` |

### LLMs Configuration


### OpenAI Configuration

| Name                         | Description                                               | Value |
| ---------------------------- | --------------------------------------------------------- | ----- |
| `config.llms.openAi.apiKey`  | OpenAI API key                                            | `""`  |
| `config.llms.openAi.secret`  | Name of the existing secret to use for the OpenAI API key | `""`  |
| `config.llms.openAi.baseUrl` | OpenAI base URL                                           | `""`  |

### Anthropic Configuration

| Name                           | Description                                                  | Value |
| ------------------------------ | ------------------------------------------------------------ | ----- |
| `config.llms.anthropic.apiKey` | Anthropic API key                                            | `""`  |
| `config.llms.anthropic.secret` | Name of the existing secret to use for the Anthropic API key | `""`  |

### Google Gemini Configuration

| Name                        | Description                                                      | Value |
| --------------------------- | ---------------------------------------------------------------- | ----- |
| `config.llms.gemini.apiKey` | Google Gemini API key                                            | `""`  |
| `config.llms.gemini.secret` | Name of the existing secret to use for the Google Gemini API key | `""`  |

### Azure OpenAI Configuration

| Name                                  | Description                                                     | Value |
| ------------------------------------- | --------------------------------------------------------------- | ----- |
| `config.llms.azureOpenAi.secret`      | Name of the existing secret to use for the Azure OpenAI API key | `""`  |
| `config.llms.azureOpenAi.deployments` | Azure OpenAI deployments                                        | `[]`  |

### AWS Bedrock Configuration

| Name                                               | Description                                                                               | Value                                       |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------- |
| `config.llms.awsBedrock.region`                    | AWS Bedrock region                                                                        | `""`                                        |
| `config.llms.awsBedrock.accessKeyId`               | AWS Bedrock access key ID                                                                 | `""`                                        |
| `config.llms.awsBedrock.secretAccessKey`           | AWS Bedrock secret access key                                                             | `""`                                        |
| `config.llms.awsBedrock.sonnet3_5ModelVersionName` | Sonnet 3.5 model version name example. Usually needs a 'us.', 'global.', or 'eu.' prefix. | `anthropic.claude-3-5-sonnet-20240620-v1:0` |
| `config.llms.awsBedrock.sonnet3_7ModelVersionName` | Sonnet 3.7 model version name example. Usually needs a 'us.', 'global.', or 'eu.' prefix. | `anthropic.claude-3-7-sonnet-20250219-v1:0` |
| `config.llms.awsBedrock.sonnet4_0ModelVersionName` | Sonnet 4.0 model version name example. Usually needs a 'us.', 'global.', or 'eu.' prefix. | `anthropic.claude-sonnet-4-20250514-v1:0`   |
| `config.llms.awsBedrock.sonnet4_5ModelVersionName` | Sonnet 4.5 model version name example. Usually needs a 'us.', 'global.', or 'eu.' prefix. | `anthropic.claude-sonnet-4-5-20250929-v1:0` |
| `config.llms.awsBedrock.haiku3_5ModelVersionName`  | Haiku 3.5 model version name example. Usually needs a 'us.', 'global.', or 'eu.' prefix.  | `anthropic.claude-3-5-haiku-20241022-v1:0`  |
| `config.llms.awsBedrock.haiku4_5ModelVersionName`  | Haiku 4.5 model version name example. Usually needs a 'us.', 'global.', or 'eu.' prefix.  | `anthropic.claude-haiku-4-5-20251001-v1:0`  |
| `config.llms.awsBedrock.secret`                    | Name of the existing secret to use for the AWS Bedrock API key                            | `""`                                        |

### Google Vertex AI Configuration

| Name                                         | Description                                                         | Value |
| -------------------------------------------- | ------------------------------------------------------------------- | ----- |
| `config.llms.googleVertexAi.projectId`       | Google Vertex AI project id                                         | `""`  |
| `config.llms.googleVertexAi.location`        | Google Vertex AI location                                           | `""`  |
| `config.llms.googleVertexAi.credentialsJson` | Google Vertex AI credentials JSON                                   | `""`  |
| `config.llms.googleVertexAi.secret`          | Name of the existing secret to use for the Google Vertex AI API key | `""`  |

### authentication Configuration


### Basic Auth configuration

| Name                                               | Description                                           | Value   |
| -------------------------------------------------- | ----------------------------------------------------- | ------- |
| `config.authentication.basicAuth.enabled`          | Enable Basic Auth for the backend                     | `false` |
| `config.authentication.basicAuth.validEmailDomain` | Valid email domain for the application                | `""`    |
| `config.authentication.basicAuth.jwtSecret`        | JWT secret for the backend                            | `""`    |
| `config.authentication.basicAuth.secret`           | Name of the existing secret to use for the JWT secret | `""`    |

### OpenID Connect configuration

| Name                                      | Description                                               | Value   |
| ----------------------------------------- | --------------------------------------------------------- | ------- |
| `config.authentication.oidc.enabled`      | Enable OIDC for the backend                               | `false` |
| `config.authentication.oidc.discoveryUrl` | OIDC discovery URL                                        | `""`    |
| `config.authentication.oidc.clientId`     | OIDC client ID                                            | `""`    |
| `config.authentication.oidc.clientSecret` | OIDC client secret                                        | `""`    |
| `config.authentication.oidc.secret`       | Name of the existing secret to use for OIDC configuration | `""`    |

### Storage Buckets Configuration

| Name                                             | Description                                                        | Value                                |
| ------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------ |
| `config.storageBuckets.provider`                 | Cloud storage provider                                             | `aws`                                |
| `config.storageBuckets.extraEnvVariables`        | Extra environment variables to add to the pods for storage buckets | `{}`                                 |
| `config.storageBuckets.parsedDocuments`          | Cloud storage bucket name                                          | `llama-platform-parsed-documents`    |
| `config.storageBuckets.parsedEtl`                | Cloud storage bucket name                                          | `llama-platform-etl`                 |
| `config.storageBuckets.parsedExternalComponents` | Cloud storage bucket name                                          | `llama-platform-external-components` |
| `config.storageBuckets.parsedFileParsing`        | Cloud storage bucket name                                          | `llama-platform-file-parsing`        |
| `config.storageBuckets.parsedRawFile`            | Cloud storage bucket name                                          | `llama-platform-raw-files`           |
| `config.storageBuckets.parseOutput`              | Cloud storage bucket name                                          | `llama-cloud-parse-output`           |
| `config.storageBuckets.parsedFileScreenshot`     | Cloud storage bucket name                                          | `llama-platform-file-screenshots`    |
| `config.storageBuckets.extractOutput`            | Cloud storage bucket name                                          | `llama-platform-extract-output`      |
| `config.storageBuckets.parseFileUpload`          | Cloud storage bucket name                                          | `llama-platform-file-parsing`        |
| `config.storageBuckets.parseFileOutput`          | Cloud storage bucket name                                          | `llama-platform-file-parsing`        |

### S3Proxy Configuration (only used when provider is set to gcp or azure, ignored for aws)

| Name                                            | Description                                                                  | Value                                      |
| ----------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------ |
| `config.storageBuckets.s3proxy.enabled`         | S3Proxy image                                                                | `false`                                    |
| `config.storageBuckets.s3proxy.image`           | S3Proxy image                                                                | `docker.io/andrewgaul/s3proxy:sha-82e50ee` |
| `config.storageBuckets.s3proxy.imagePullPolicy` | S3Proxy image pull policy                                                    | `IfNotPresent`                             |
| `config.storageBuckets.s3proxy.containerPort`   | S3Proxy container port                                                       | `8080`                                     |
| `config.storageBuckets.s3proxy.securityContext` | Security context for the S3Proxy container                                   | `{}`                                       |
| `config.storageBuckets.s3proxy.resources`       | Set container requests and limits for different resources like CPU or memory | `{}`                                       |
| `config.storageBuckets.s3proxy.config`          | S3Proxy configuration ENV variables                                          | `{}`                                       |

### Frontend Configuration

| Name                      | Description             | Value  |
| ------------------------- | ----------------------- | ------ |
| `config.frontend.enabled` | Enable Frontend service | `true` |

### LlamaExtract Configuration

| Name                                      | Description                                                                      | Value                 |
| ----------------------------------------- | -------------------------------------------------------------------------------- | --------------------- |
| `config.extraction.multimodalModel`       | LlamaExtract multimodal model (gemini-2.0-flash, gemini-2.5-pro, openai-gpt-4-1) | `openai-gpt-4-1`      |
| `config.extraction.schemaGenerationModel` | LlamaExtract schema generation model (gemini-2.0-flash, openai-gpt-4-1-mini)     | `openai-gpt-4-1-mini` |
| `config.extraction.maxPages`              | LlamaExtract max pages allowed                                                   | `500`                 |
| `config.extraction.maxFileSizeMb`         | LlamaExtract max file size (MB) allowed                                          | `100`                 |

### Jobs Configuration

| Name                                                 | Description                                                   | Value      |
| ---------------------------------------------------- | ------------------------------------------------------------- | ---------- |
| `config.jobs.maxJobsInExecutionPerJobType`           | Maximum number of jobs in execution per job type              | `10`       |
| `config.jobs.maxIndexJobsInExecution`                | Maximum number of index jobs in execution                     | `0`        |
| `config.jobs.maxDocumentIngestionJobsInExecution`    | Maximum number of document ingestion jobs in execution        | `1`        |
| `config.jobs.includeJobErrorDetails`                 | Whether to always include job error details in API and the UI | `true`     |
| `config.jobs.defaultTransformDocumentTimeoutSeconds` | Default timeout in seconds for document transformation jobs   | `240`      |
| `config.jobs.transformEmbeddingCharLimit`            | Character limit for transform embedding operations            | `11520000` |

### LlamaParse Configuration

| Name                                                                  | Description                                                | Value   |
| --------------------------------------------------------------------- | ---------------------------------------------------------- | ------- |
| `config.parse.debugMode`                                              | Enable debug mode for LlamaParse                           | `false` |
| `config.parse.maxQueueConcurrency`                                    | Max number of jobs the worker can process at the same time | `3`     |
| `config.parse.preferedPremiumModel`                                   | Prefered premium LLM model to use for the application      | `""`    |
| `config.parse.concurrency.accurateModeLLMConcurrency`                 | concurrency setting                                        | `""`    |
| `config.parse.concurrency.multimodalModelConcurrency`                 | concurrency setting                                        | `""`    |
| `config.parse.concurrency.premiumModeModelConcurrency`                | concurrency setting                                        | `""`    |
| `config.parse.concurrency.ocrConcurrency`                             | ocr concurrency setting                                    | `""`    |
| `config.parse.concurrency.layoutExtractionConcurrency`                | layout extraction concurrency setting                      | `""`    |
| `config.parse.concurrency.layoutExtractionV2Concurrency`              | layout extraction v2 concurrency setting                   | `""`    |
| `config.parse.concurrency.layoutModeBlockParseConcurrency`            | layout mode block parse concurrency setting                | `""`    |
| `config.parse.concurrency.layoutModePageConcurrency`                  | layout mode page concurrency setting                       | `""`    |
| `config.parse.concurrency.layoutModeReadingOrderDetectionConcurrency` | layout mode reading order detection concurrency setting    | `""`    |
| `config.parse.concurrency.gemini25Flash`                              | gemini25Flash concurrency setting                          | `""`    |
| `config.parse.concurrency.gemini25Pro`                                | gemini25Pro concurrency setting                            | `""`    |
| `config.parse.concurrency.gemini20Flash`                              | gemini20Flash concurrency setting                          | `""`    |
| `config.parse.concurrency.gemini20FlashLite`                          | gemini20FlashLite concurrency setting                      | `""`    |
| `config.parse.concurrency.gemini15Flash`                              | gemini15Flash concurrency setting                          | `""`    |
| `config.parse.concurrency.gemini15Pro`                                | gemini15Pro concurrency setting                            | `""`    |
| `config.parse.concurrency.openaiGpt4oMini`                            | openaiGpt4oMini concurrency setting                        | `""`    |
| `config.parse.concurrency.openaiGpt4o`                                | openaiGpt4o concurrency setting                            | `""`    |
| `config.parse.concurrency.openaiGpt41`                                | openaiGpt41 concurrency setting                            | `""`    |
| `config.parse.concurrency.openaiGpt41Mini`                            | openaiGpt41Mini concurrency setting                        | `""`    |
| `config.parse.concurrency.openaiGpt41Nano`                            | openaiGpt41Nano concurrency setting                        | `""`    |
| `config.parse.concurrency.openaiGpt5`                                 | openaiGpt5 concurrency setting                             | `""`    |
| `config.parse.concurrency.openaiGpt5Mini`                             | openaiGpt5Mini concurrency setting                         | `""`    |
| `config.parse.concurrency.openaiGpt5Nano`                             | openaiGpt5Nano concurrency setting                         | `""`    |
| `config.parse.concurrency.openaiWhisper1`                             | openaiWhisper1 concurrency setting                         | `""`    |
| `config.parse.concurrency.anthropicSonnet37`                          | anthropicSonnet37 concurrency setting                      | `""`    |
| `config.parse.concurrency.anthropicSonnet35`                          | anthropicSonnet35 concurrency setting                      | `""`    |
| `config.parse.concurrency.anthropicSonnet40`                          | anthropicSonnet40 concurrency setting                      | `""`    |
| `config.parse.concurrency.anthropicSonnet45`                          | anthropicSonnet45 concurrency setting                      | `""`    |
| `config.parse.concurrency.anthropicHaiku35`                           | anthropicHaiku35 concurrency setting                       | `""`    |
| `config.parse.concurrency.anthropicHaiku45`                           | anthropicHaiku45 concurrency setting                       | `""`    |

### LlamaParse-OCR Configuration

| Name                                  | Description                                                                | Value   |
| ------------------------------------- | -------------------------------------------------------------------------- | ------- |
| `config.parseOcr.enabled`             | Enable LlamaParseOcr                                                       | `true`  |
| `config.parseOcr.gpu`                 | Enable GPU acceleration for OCR processing (if false, uses CPU backend)    | `false` |
| `config.parseLayoutDetection.enabled` | Enable LlamaParse Layout Detection                                         | `true`  |
| `config.parseLayoutDetection.gpu`     | Enable GPU acceleration for Layout processing (if false, uses CPU backend) | `false` |

### Layout Detection V3 (BYOC Self-Hosted) Configuration

| Name                                    | Description                                              | Value   |
| --------------------------------------- | -------------------------------------------------------- | ------- |
| `config.parseLayoutDetectionV3.enabled` | Enable Layout V3 Detection (self-hosted RT-DETRv2 model) | `false` |
| `config.parseLayoutDetectionV3.gpu`     | Enable GPU acceleration for Layout V3 processing         | `false` |

### Temporal Configuration

| Name                                                     | Description                                                                                   | Value                                   |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------- |
| `config.temporal.workerRegistryProfile`                  | Temporal worker registry profile (default or consolidated)                                    | `consolidated`                          |
| `config.temporal.namespace`                              | Temporal registered namespace                                                                 | `""`                                    |
| `config.temporal.searchAttributesJob.enabled`            | Enable the search attributes job                                                              | `true`                                  |
| `config.temporal.searchAttributesJob.image`              | Image for temporal admin tools                                                                | `docker.io/temporalio/admin-tools:1.29` |
| `config.temporal.searchAttributesJob.attributes[0].name` | Name of the first search attribute                                                            | `Project`                               |
| `config.temporal.searchAttributesJob.attributes[0].type` | Type of the first search attribute (Text, Keyword, Int, Double, Bool, Datetime, KeywordList)  | `Keyword`                               |
| `config.temporal.searchAttributesJob.attributes[1].name` | Name of the second search attribute                                                           | `Organization`                          |
| `config.temporal.searchAttributesJob.attributes[1].type` | Type of the second search attribute (Text, Keyword, Int, Double, Bool, Datetime, KeywordList) | `Keyword`                               |

### Common Configuration

| Name                | Description                                          | Value |
| ------------------- | ---------------------------------------------------- | ----- |
| `commonLabels`      | Labels to add to all deployed objects                | `{}`  |
| `commonAnnotations` | Annotations to add to all deployed objects           | `{}`  |
| `imagePullSecrets`  | Image pull secrets to use for the images string list | `[]`  |
| `extraObjects`      |                                                      | `[]`  |

### Frontend Configuration

| Name                                   | Description                                                                                                       | Value                                            |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `frontend.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                             |
| `frontend.annotations`                 | Annotations added to the Frontend Deployment.                                                                     | `{}`                                             |
| `frontend.image`                       | Frontend image                                                                                                    | `docker.io/llamaindex/llamacloud-frontend:0.7.0` |
| `frontend.imagePullPolicy`             | Frontend image pull policy                                                                                        | `IfNotPresent`                                   |
| `frontend.securityContext`             | Security context for the container                                                                                | `{}`                                             |
| `frontend.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                             |
| `frontend.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                             |
| `frontend.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                             |
| `frontend.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                             |
| `frontend.topologySpreadConstraints`   | Topology Spread Constraints for frontend pods                                                                     | `[]`                                             |
| `frontend.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                             |
| `frontend.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                             |
| `frontend.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                             |
| `frontend.extraEnvVariables`           | Extra environment variables to add to Frontend pods                                                               | `[]`                                             |
| `frontend.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                             |
| `frontend.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                             |

### Backend Configuration

| Name                                  | Description                                                                                                       | Value                                           |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `backend.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                            |
| `backend.annotations`                 | Annotations added to the Backend Deployment.                                                                      | `{}`                                            |
| `backend.image`                       | Backend image                                                                                                     | `docker.io/llamaindex/llamacloud-backend:0.7.0` |
| `backend.imagePullPolicy`             | Backend image pull policy                                                                                         | `IfNotPresent`                                  |
| `backend.securityContext`             | Security context for the container                                                                                | `{}`                                            |
| `backend.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                            |
| `backend.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                            |
| `backend.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                            |
| `backend.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                            |
| `backend.topologySpreadConstraints`   | Topology Spread Constraints for backend pods                                                                      | `[]`                                            |
| `backend.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `backend.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `backend.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                            |
| `backend.extraEnvVariables`           | Extra environment variables to add to Backend pods                                                                | `[]`                                            |
| `backend.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                            |
| `backend.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                            |

### JobsService Configuration

| Name                                      | Description                                                                                                       | Value                                           |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `jobsService.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                            |
| `jobsService.annotations`                 | Annotations added to the JobsService Deployment.                                                                  | `{}`                                            |
| `jobsService.image`                       | JobsService image                                                                                                 | `docker.io/llamaindex/llamacloud-backend:0.7.0` |
| `jobsService.imagePullPolicy`             | JobsService image pull policy                                                                                     | `IfNotPresent`                                  |
| `jobsService.securityContext`             | Security context for the container                                                                                | `{}`                                            |
| `jobsService.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                            |
| `jobsService.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                            |
| `jobsService.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                            |
| `jobsService.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                            |
| `jobsService.topologySpreadConstraints`   | Topology Spread Constraints for JobsService pods                                                                  | `[]`                                            |
| `jobsService.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `jobsService.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `jobsService.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                            |
| `jobsService.extraEnvVariables`           | Extra environment variables to add to JobsService pods                                                            | `[]`                                            |
| `jobsService.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                            |
| `jobsService.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                            |

### JobsWorker Configuration

| Name                                     | Description                                                                                                       | Value                                           |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `jobsWorker.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                            |
| `jobsWorker.annotations`                 | Annotations added to the JobsWorker Deployment.                                                                   | `{}`                                            |
| `jobsWorker.image`                       | JobsWorker image                                                                                                  | `docker.io/llamaindex/llamacloud-backend:0.7.0` |
| `jobsWorker.imagePullPolicy`             | JobsWorker image pull policy                                                                                      | `IfNotPresent`                                  |
| `jobsWorker.securityContext`             | Security context for the container                                                                                | `{}`                                            |
| `jobsWorker.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                            |
| `jobsWorker.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                            |
| `jobsWorker.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                            |
| `jobsWorker.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                            |
| `jobsWorker.topologySpreadConstraints`   | Topology Spread Constraints for JobsWorker pods                                                                   | `[]`                                            |
| `jobsWorker.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `jobsWorker.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `jobsWorker.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                            |
| `jobsWorker.extraEnvVariables`           | Extra environment variables to add to JobsWorker pods                                                             | `[]`                                            |
| `jobsWorker.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                            |
| `jobsWorker.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                            |

### LlamaParse Configuration

| Name                                     | Description                                                                                                       | Value                                              |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `llamaParse.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                               |
| `llamaParse.annotations`                 | Annotations added to the LlamaParse Deployment.                                                                   | `{}`                                               |
| `llamaParse.image`                       | LlamaParse image                                                                                                  | `docker.io/llamaindex/llamacloud-llamaparse:0.7.0` |
| `llamaParse.imagePullPolicy`             | LlamaParse image pull policy                                                                                      | `IfNotPresent`                                     |
| `llamaParse.securityContext`             | Security context for the container                                                                                | `{}`                                               |
| `llamaParse.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                               |
| `llamaParse.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                               |
| `llamaParse.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                               |
| `llamaParse.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                               |
| `llamaParse.topologySpreadConstraints`   | Topology Spread Constraints for LlamaParse pods                                                                   | `[]`                                               |
| `llamaParse.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                               |
| `llamaParse.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                               |
| `llamaParse.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                               |
| `llamaParse.extraEnvVariables`           | Extra environment variables to add to LlamaParse pods                                                             | `[]`                                               |
| `llamaParse.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                               |
| `llamaParse.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                               |

### LlamaParseOcr Configuration

| Name                                        | Description                                                                                                       | Value                                                  |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `llamaParseOcr.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                                   |
| `llamaParseOcr.annotations`                 | Annotations added to the LlamaParseOcr Deployment.                                                                | `{}`                                                   |
| `llamaParseOcr.image`                       | LlamaParseOcr image                                                                                               | `docker.io/llamaindex/llamacloud-llamaparse-ocr:0.7.0` |
| `llamaParseOcr.imagePullPolicy`             | LlamaParseOcr image pull policy                                                                                   | `IfNotPresent`                                         |
| `llamaParseOcr.securityContext`             | Security context for the container                                                                                | `{}`                                                   |
| `llamaParseOcr.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                                   |
| `llamaParseOcr.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                                   |
| `llamaParseOcr.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                                   |
| `llamaParseOcr.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                                   |
| `llamaParseOcr.topologySpreadConstraints`   | Topology Spread Constraints for LlamaParseOcr pods                                                                | `[]`                                                   |
| `llamaParseOcr.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                                   |
| `llamaParseOcr.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                                   |
| `llamaParseOcr.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                                   |
| `llamaParseOcr.extraEnvVariables`           | Extra environment variables to add to LlamaParseOcr pods                                                          | `[]`                                                   |
| `llamaParseOcr.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                                   |
| `llamaParseOcr.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                                   |

### LlamaParse Layout Detection API Configuration

| Name                                                       | Description                                                                                                       | Value                                                        |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `llamaParseLayoutDetectionApi.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                                         |
| `llamaParseLayoutDetectionApi.annotations`                 | Annotations added to the LlamaParseLayoutDetectionApi Deployment.                                                 | `{}`                                                         |
| `llamaParseLayoutDetectionApi.image`                       | LlamaParseLayoutDetectionApi image                                                                                | `docker.io/llamaindex/llamacloud-layout-detection-api:0.7.0` |
| `llamaParseLayoutDetectionApi.imagePullPolicy`             | LlamaParseLayoutDetectionApi image pull policy                                                                    | `IfNotPresent`                                               |
| `llamaParseLayoutDetectionApi.securityContext`             | Security context for the container                                                                                | `{}`                                                         |
| `llamaParseLayoutDetectionApi.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                                         |
| `llamaParseLayoutDetectionApi.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                                         |
| `llamaParseLayoutDetectionApi.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                                         |
| `llamaParseLayoutDetectionApi.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                                         |
| `llamaParseLayoutDetectionApi.topologySpreadConstraints`   | Topology Spread Constraints for LlamaParseLayoutDetectionApi pods                                                 | `[]`                                                         |
| `llamaParseLayoutDetectionApi.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                                         |
| `llamaParseLayoutDetectionApi.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                                         |
| `llamaParseLayoutDetectionApi.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                                         |
| `llamaParseLayoutDetectionApi.extraEnvVariables`           | Extra environment variables to add to LlamaParseLayoutDetectionApi pods                                           | `[]`                                                         |
| `llamaParseLayoutDetectionApi.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                                         |
| `llamaParseLayoutDetectionApi.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                                         |

### LlamaParse Layout Detection API V3 Configuration (BYOC)

| Name                                                         | Description                                                                                                       | Value          |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | -------------- |
| `llamaParseLayoutDetectionApiV3.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`           |
| `llamaParseLayoutDetectionApiV3.annotations`                 | Annotations added to the LlamaParseLayoutDetectionApiV3 Deployment.                                               | `{}`           |
| `llamaParseLayoutDetectionApiV3.image`                       | LlamaParseLayoutDetectionApiV3 image (RT-DETRv2 + figure classifier)                                              | `""`           |
| `llamaParseLayoutDetectionApiV3.imagePullPolicy`             | LlamaParseLayoutDetectionApiV3 image pull policy                                                                  | `IfNotPresent` |
| `llamaParseLayoutDetectionApiV3.securityContext`             | Security context for the container                                                                                | `{}`           |
| `llamaParseLayoutDetectionApiV3.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`           |
| `llamaParseLayoutDetectionApiV3.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`           |
| `llamaParseLayoutDetectionApiV3.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`           |
| `llamaParseLayoutDetectionApiV3.affinity`                    | Pod scheduling constraints                                                                                        | `{}`           |
| `llamaParseLayoutDetectionApiV3.topologySpreadConstraints`   | Topology Spread Constraints for LlamaParseLayoutDetectionApiV3 pods                                               | `[]`           |
| `llamaParseLayoutDetectionApiV3.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`           |
| `llamaParseLayoutDetectionApiV3.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`           |
| `llamaParseLayoutDetectionApiV3.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`           |
| `llamaParseLayoutDetectionApiV3.extraEnvVariables`           | Extra environment variables to add to LlamaParseLayoutDetectionApiV3 pods                                         | `[]`           |
| `llamaParseLayoutDetectionApiV3.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`           |
| `llamaParseLayoutDetectionApiV3.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`           |

### Usage Configuration

| Name                                | Description                                                                                                       | Value                                           |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `usage.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                            |
| `usage.annotations`                 | Annotations added to the LlamaParseLayoutDetectionApi Deployment.                                                 | `{}`                                            |
| `usage.image`                       | LlamaParseLayoutDetectionApi image                                                                                | `docker.io/llamaindex/llamacloud-backend:0.7.0` |
| `usage.imagePullPolicy`             | LlamaParseLayoutDetectionApi image pull policy                                                                    | `IfNotPresent`                                  |
| `usage.securityContext`             | Security context for the container                                                                                | `{}`                                            |
| `usage.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                            |
| `usage.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                            |
| `usage.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                            |
| `usage.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                            |
| `usage.topologySpreadConstraints`   | Topology Spread Constraints for usage pods                                                                        | `[]`                                            |
| `usage.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `usage.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `usage.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                            |
| `usage.extraEnvVariables`           | Extra environment variables to add to LlamaParseLayoutDetectionApi pods                                           | `[]`                                            |
| `usage.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                            |
| `usage.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                            |

### Temporal Workloads Configuration

| Name                                                        | Description                                                                                                       | Value                                              |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `temporalWorkloads.llamaParse.horizontalPodAutoscalerSpec`  | HorizontalPodAutoScaler configuration                                                                             | `{}`                                               |
| `temporalWorkloads.llamaParse.annotations`                  | Annotations added to the temporal llamaparse Deployment.                                                          | `{}`                                               |
| `temporalWorkloads.llamaParse.image`                        | temporal llamaparse image                                                                                         | `docker.io/llamaindex/llamacloud-llamaparse:0.7.0` |
| `temporalWorkloads.llamaParse.imagePullPolicy`              | temporal llamaparse image pull policy                                                                             | `IfNotPresent`                                     |
| `temporalWorkloads.llamaParse.securityContext`              | Security context for the container                                                                                | `{}`                                               |
| `temporalWorkloads.llamaParse.serviceAccountAnnotations`    | Annotations to add to the service account                                                                         | `{}`                                               |
| `temporalWorkloads.llamaParse.nodeSelector`                 | Node labels for pod assignment                                                                                    | `{}`                                               |
| `temporalWorkloads.llamaParse.tolerations`                  | Taints to tolerate on node assignment:                                                                            | `[]`                                               |
| `temporalWorkloads.llamaParse.affinity`                     | Pod scheduling constraints                                                                                        | `{}`                                               |
| `temporalWorkloads.llamaParse.topologySpreadConstraints`    | Topology Spread Constraints for temporal llamaparse pods                                                          | `[]`                                               |
| `temporalWorkloads.llamaParse.podAnnotations`               | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                               |
| `temporalWorkloads.llamaParse.podSecurityContext`           | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                               |
| `temporalWorkloads.llamaParse.resources`                    | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                               |
| `temporalWorkloads.llamaParse.extraEnvVariables`            | Extra environment variables to add to temporal llamaparse pods                                                    | `[]`                                               |
| `temporalWorkloads.llamaParse.volumeMounts`                 | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                               |
| `temporalWorkloads.llamaParse.volumes`                      | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                               |
| `temporalWorkloads.jobsService.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                               |
| `temporalWorkloads.jobsService.annotations`                 | Annotations added to the temporal jobsService Deployment.                                                         | `{}`                                               |
| `temporalWorkloads.jobsService.image`                       | temporal jobsService image                                                                                        | `docker.io/llamaindex/llamacloud-backend:0.7.0`    |
| `temporalWorkloads.jobsService.imagePullPolicy`             | temporal jobsService image pull policy                                                                            | `IfNotPresent`                                     |
| `temporalWorkloads.jobsService.securityContext`             | Security context for the container                                                                                | `{}`                                               |
| `temporalWorkloads.jobsService.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                               |
| `temporalWorkloads.jobsService.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                               |
| `temporalWorkloads.jobsService.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                               |
| `temporalWorkloads.jobsService.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                               |
| `temporalWorkloads.jobsService.topologySpreadConstraints`   | Topology Spread Constraints for temporal jobsService pods                                                         | `[]`                                               |
| `temporalWorkloads.jobsService.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                               |
| `temporalWorkloads.jobsService.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                               |
| `temporalWorkloads.jobsService.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                               |
| `temporalWorkloads.jobsService.extraEnvVariables`           | Extra environment variables to add to temporal jobsService pods                                                   | `[]`                                               |
| `temporalWorkloads.jobsService.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                               |
| `temporalWorkloads.jobsService.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                               |

### Temporal Workers Configuration

| Name                                                                         | Description                                                                                                       | Value                                           |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `temporalWorkloads.workers.temporal-jobs-worker.horizontalPodAutoscalerSpec` | HorizontalPodAutoScaler configuration                                                                             | `{}`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.annotations`                 | Annotations added to the temporal-jobs-worker Deployment.                                                         | `{}`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.image`                       | Frontend image                                                                                                    | `docker.io/llamaindex/llamacloud-backend:0.7.0` |
| `temporalWorkloads.workers.temporal-jobs-worker.imagePullPolicy`             | Frontend image pull policy                                                                                        | `IfNotPresent`                                  |
| `temporalWorkloads.workers.temporal-jobs-worker.command`                     | Command to run in the container                                                                                   | `[]`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.securityContext`             | Security context for the container                                                                                | `{}`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.serviceAccountAnnotations`   | Annotations to add to the service account                                                                         | `{}`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.nodeSelector`                | Node labels for pod assignment                                                                                    | `{}`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.tolerations`                 | Taints to tolerate on node assignment:                                                                            | `[]`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.affinity`                    | Pod scheduling constraints                                                                                        | `{}`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.topologySpreadConstraints`   | Topology Spread Constraints for temporal-jobs-worker pods                                                         | `[]`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.podAnnotations`              | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.podSecurityContext`          | Annotations to add to the resulting Pods of the Deployment.                                                       | `{}`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.resources`                   | Set container requests and limits for different resources like CPU or memory (essential for production workloads) | `{}`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.extraEnvVariables`           | Extra environment variables to add to temporal-jobs-worker pods                                                   | `[]`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.volumeMounts`                | List of volumeMounts that can be mounted by containers belonging to the pod                                       | `[]`                                            |
| `temporalWorkloads.workers.temporal-jobs-worker.volumes`                     | List of volumes that can be mounted by containers belonging to the pod                                            | `[]`                                            |
