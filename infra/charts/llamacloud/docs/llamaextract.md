# LlamaExtract

LlamaExtract is a component of LlamaCloud that enables you to extract structured data from unstructured documents. It is available as a web UI, a Python SDK, and a REST API.

For in-depth information about how LlamaExtract, please refer to our [public docs](https://docs.cloud.llamaindex.ai/llamaextract/getting_started).

## Setup

To enable LlamaExtract in your BYOC deployment, you'll need to do a few things:

- **Make sure your deployment is running version `0.3.0` or higher**
- **Create a new LlamaExtract filestorage bucket in your cloud provider**
    - The bucket name LlamaCloud will store LlamaExtract specific files from is `llama-platform-extract-output`. This can be overriden by setting `.Values.global.config.llamaExtractOutputCloudBucketName` to your desired bucket name in your `values.yaml` file.
- **Configure the backend pod LLM access**
    - If you haven't done this already to enable other LlamaCloud features, you'll need to do so now.
    - You will need to configure the `backend` sevice to have access to OpenAI's `gpt4o` model.
    - OpenAI credentials can be added at either `.Values.backend.config.openAiApiKey` or via a secret object reference at `.Values.backend.config.existingOpenAiApiKeySecretName`.
    - You can also configured Azure OpenAI credentials at `.Values.backend.config.azureOpenAi.enabled` with either static credentials at `.Values.backend.config.azureOpenAi.key` and `.Values.backend.config.azureOpenAi.endpoint` and other fields for the Azure OpenAI configuration or a secret object reference at `.Values.backend.config.azureOpenAi.existingSecret`.
- **Configure LlamaParse LLM access**
    - Similarly to the backend pod, you'll need to configure the `llamaParse` service to have access to OpenAI, but this time for the `gpt4o-mini` model.
    - OpenAI credentials can be added at either `.Values.llamaParse.config.openAiApiKey` or via a secret object reference at `.Values.llamaParse.config.existingOpenAiApiKeySecretName`.
    - You can also configured Azure OpenAI credentials at `.Values.llamaParse.config.azureOpenAi.enabled` with either static credentials at `.Values.llamaParse.config.azureOpenAi.key` and `.Values.llamaParse.config.azureOpenAi.endpoint` and other fields for the Azure OpenAI configuration or a secret object reference at `.Values.llamaParse.config.azureOpenAi.existingSecret`.
