{{/*
Jobs Worker Component Settings.
*/}}
{{ define "llamacloud.component.jobsWorker" }}
{{- $component := .Values.jobsWorker }}
{{- $component = set $component "prefix" "llamacloud.component.jobsWorker" }}
{{- $component = set $component "name" "llamacloud-worker" }}
{{- $component = set $component "image" ($.Values.jobsWorker).image | default ( print "docker.io/llamaindex/llamacloud-backend:" .Chart.AppVersion ) }}
{{- $component = set $component "imagePullPolicy" ( ($.Values.jobsWorker).imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 8001 }}
{{- $component = set $component "command" (list "start_consumer") }}
{{- $component = set $component "usesS3" "true" }}
{{- $component | toYaml }}
{{- end }}

{{/*
Jobs Worker Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.jobsWorker.resources" }}
requests:
  cpu: {{ (((.component).resources).requests).cpu | default "500m" }}
  memory: {{ (((.component).resources).requests).memory | default "4Gi" }}
limits:
  cpu: {{ (((.component).resources).limits).cpu | default "2" }}
  memory: {{ (((.component).resources).limits).memory | default "6Gi" }}
{{- end }}

{{/*
Jobs Worker Liveness Probe.
*/}}
{{ define "llamacloud.component.jobsWorker.livenessProbe" }}
httpGet:
  path: /api/health
  port: http
initialDelaySeconds: 30
periodSeconds: 15
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Jobs Worker Readiness Probe.
*/}}
{{ define "llamacloud.component.jobsWorker.readinessProbe" }}
httpGet:
  path: /api/health
  port: http
initialDelaySeconds: 30
periodSeconds: 15
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Jobs Worker Startup Probe.
*/}}
{{ define "llamacloud.component.jobsWorker.startupProbe" }}
httpGet:
  path: /api/health
  port: http
initialDelaySeconds: 30
periodSeconds: 15
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Jobs Worker Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.jobsWorker.env" }}
{{- if (.component).extraEnvVariables }}
{{ toYaml (.component).extraEnvVariables }}
{{- end }}
{{- end }}

{{/*
Jobs Worker Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.jobsWorker.envFrom" }}
{{- include "llamacloud.secrets.license" .root}}
- configMapRef:
    name: bucket-config
- configMapRef:
    name: common-config
- configMapRef:
    name: extract-config
- configMapRef:
    name: urls-config
{{- if (include "llamacloud.component.jobsWorker.configMap" $) }}
- configMapRef:
    name: {{ .component.name }}
{{- end }}
{{- if (include "llamacloud.component.jobsWorker.secret" $) }}
- secretRef:
    name: {{ .component.name }}
{{- end }}
- secretRef:
    name: bucket-secret
{{- include "llamacloud.secrets.postgresql" .root }}
{{- include "llamacloud.secrets.mongodb" .root }}
{{- include "llamacloud.secrets.rabbitmq" .root }}
{{- include "llamacloud.secrets.redis" .root }}
{{- include "llamacloud.secrets.qdrant" .root }}
{{- include "llamacloud.secrets.basicAuth" .root }}
{{- include "llamacloud.secrets.oidc" .root }}
{{- include "llamacloud.secrets.openAi" .root }}
{{- include "llamacloud.secrets.anthropic" .root }}
{{- include "llamacloud.secrets.gemini" .root }}
{{- include "llamacloud.secrets.azureOpenAi" .root }}
{{- include "llamacloud.secrets.awsBedrock" .root }}
{{- include "llamacloud.secrets.googleVertexAi" .root }}
{{- end }}

{{/*
Jobs Worker Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.jobsWorker.secret" }}
{{- end }}

{{/*
Jobs Worker ConfigMap. 

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.jobsWorker.configMap" }}
JOB_CONSUMER_PORT: "80"

MAX_JOBS_IN_EXECUTION_PER_JOB_TYPE: {{ ((.root.Values.config).jobs).maxJobsInExecutionPerJobType | default 10 | quote }}
MAX_INDEX_JOBS_IN_EXECUTION: {{ ((.root.Values.config).jobs).maxIndexJobsInExecution | default 0 | quote }}
MAX_DOCUMENT_INGESTION_JOBS_IN_EXECUTION: {{ ((.root.Values.config).jobs).maxDocumentIngestionJobsInExecution | default 1 | quote }}
INCLUDE_JOB_ERROR_DETAILS: {{ ((.root.Values.config).jobs).includeJobErrorDetails | default "true" | quote }}
DEFAULT_TRANSFORM_DOCUMENT_TIMEOUT_SECONDS: {{ ((.root.Values.config).jobs).defaultTransformDocumentTimeoutSeconds | default "240" | quote }}
TRANSFORM_EMBEDDING_CHAR_LIMIT: {{ ((.root.Values.config).jobs).transformEmbeddingCharLimit | default "11520000" | quote }}
{{- end }}

{{/*
Jobs Worker Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.jobsWorker.volumeMounts" }}
- mountPath: /tmp
  name: tmp
{{- if (.component).volumeMounts }}
{{ toYaml (.component).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Jobs Worker Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.jobsWorker.volumes" }}
- emptyDir: {}
  name: tmp
{{- if (((.root.Values.config).storageBuckets).s3proxy.enabled | default false) }}
- emptyDir: {}
  name: s3proxy-tmp
{{- end }}
{{- if (.component).volumes }}
{{ toYaml (.component).volumes }}
{{- end }}
{{- end }}