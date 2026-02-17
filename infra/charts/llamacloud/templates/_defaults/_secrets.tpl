{{/*
License Secret envFrom
*/}}
{{ define "llamacloud.secrets.license" }}
{{- if (.Values.license).secret }}
- secretRef:
    name: {{ .Values.license.secret }}
{{- else }}
- secretRef:
    name: llamacloud-license-key
{{- end }}
{{- end }}

{{/*
PostgreSQL Secret envFrom
*/}}
{{ define "llamacloud.secrets.postgresql" }}
{{- if (.Values.postgresql).secret }}
- secretRef:
    name: {{ .Values.postgresql.secret }}
{{- else }}
- secretRef:
    name: "postgresql-secret"
{{- end }}
{{- end }}

{{/*
MongoDB Secret envFrom
*/}}
{{ define "llamacloud.secrets.mongodb" }}
{{- if (.Values.mongodb).secret }}
- secretRef:
    name: {{ .Values.mongodb.secret }}
{{- else }}
- secretRef:
    name: "mongodb-secret"
{{- end }}
{{- end }}

{{/*
RabbitMQ Secret envFrom
*/}}
{{ define "llamacloud.secrets.rabbitmq" }}
{{- if (.Values.rabbitmq).secret }}
- secretRef:
    name: {{ .Values.rabbitmq.secret }}
{{- else }}
- secretRef:
    name: "rabbitmq-secret"
{{- end }}
{{- end }}

{{/*
Redis Secret envFrom
*/}}
{{ define "llamacloud.secrets.redis" }}
{{- if (.Values.redis).secret }}
- secretRef:
    name: {{ .Values.redis.secret }}
{{- else }}
- secretRef:
    name: "redis-secret"
{{- end }}
{{- end }}

{{/*
Qdrant Secret envFrom
*/}}
{{ define "llamacloud.secrets.qdrant" }}
{{- if ( and (.Values.qdrant).enabled (.Values.qdrant).secret ) }}
- secretRef:
    name: {{ .Values.qdrant.secret }}
{{- else if (.Values.qdrant).enabled }}
- secretRef:
    name: "qdrant-secret"
{{- end }}
{{- end }}

{{/*
Basic Auth Secret envFrom
*/}}
{{ define "llamacloud.secrets.basicAuth" }}
{{- if ( and (((.Values.config).authentication).basicAuth).enabled (((.Values.config).authentication).basicAuth).secret ) }}
- secretRef:
    name: {{ .Values.config.authentication.basicAuth.secret }}
{{- else if (((.Values.config).authentication).basicAuth).enabled }}
- secretRef:
    name: "basic-auth-secret"
{{- end }}
{{- end }}

{{/*
OIDC Secret envFrom
*/}}
{{ define "llamacloud.secrets.oidc" }}
{{- if ( and (((.Values.config).authentication).oidc).enabled (((.Values.config).authentication).oidc).secret ) }}
- secretRef:
    name: {{ .Values.config.authentication.oidc.secret }}
{{- else if (((.Values.config).authentication).oidc).enabled }}
- secretRef:
    name: "oidc-secret"
{{- end }}
{{- end }}

{{/*
OpenAI Secret envFrom
*/}}
{{ define "llamacloud.secrets.openAi" }}
{{- if (((.Values.config).llms).openAi).secret }}
- secretRef:
    name: {{ .Values.config.llms.openAi.secret }}
{{- else if (((.Values.config).llms).openAi).apiKey }}
- secretRef:
    name: "openai-api-key-secret"
{{- end }}
{{- end }}

{{/*
Anthropic Secret envFrom
*/}}
{{ define "llamacloud.secrets.anthropic" }}
{{- if (((.Values.config).llms).anthropic).secret }}
- secretRef:
    name: {{ .Values.config.llms.anthropic.secret }}
{{- else if (((.Values.config).llms).anthropic).apiKey }}
- secretRef:
    name: "anthropic-api-key-secret"
{{- end }}
{{- end }}

{{/*
Gemini Secret envFrom
*/}}
{{ define "llamacloud.secrets.gemini" }}
{{- if (((.Values.config).llms).gemini).secret }}
- secretRef:
    name: {{ .Values.config.llms.gemini.secret }}
{{- else if (((.Values.config).llms).gemini).apiKey }}
- secretRef:
    name: "gemini-api-key-secret"
{{- end }}
{{- end }}

{{/*
Azure Open AI Secret envFrom
*/}}
{{ define "llamacloud.secrets.azureOpenAi" }}
{{- if (((.Values.config).llms).azureOpenAi).secret }}
- secretRef:
    name: {{ .Values.config.llms.azureOpenAi.secret }}
{{- else if (((.Values.config).llms).azureOpenAi).deployments }}
- secretRef:
    name: "azure-open-ai-api-key-secret"
{{- end }}
{{- end }}

{{/*
AWS Bedrock Secret envFrom
*/}}
{{ define "llamacloud.secrets.awsBedrock" }}
{{- if (((.Values.config).llms).awsBedrock).secret }}
- secretRef:
    name: {{ .Values.config.llms.awsBedrock.secret }}
{{- else if and (((.Values.config).llms).awsBedrock).accessKeyId (((.Values.config).llms).awsBedrock).secretAccessKey (((.Values.config).llms).awsBedrock).region }}
- secretRef:
    name: "aws-bedrock-api-key-secret"
{{- end }}
{{- end }}

{{/*
Google Vertex AI Secret envFrom
*/}}
{{ define "llamacloud.secrets.googleVertexAi" }}
{{- if (((.Values.config).llms).googleVertexAi).secret }}
- secretRef:
    name: {{ .Values.config.llms.googleVertexAi.secret }}
{{- else if and (((.Values.config).llms).googleVertexAi).projectId (((.Values.config).llms).googleVertexAi).credentialsJson (((.Values.config).llms).googleVertexAi).location }}
- secretRef:
    name: "google-vertex-ai-api-key-secret"
{{- end }}
{{- end }}