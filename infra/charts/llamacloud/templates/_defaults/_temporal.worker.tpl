{{/*
Temporal Worker Component Settings.

Parameters:
- name: The name of the component
- component: The component configuration in values.yaml
- appVersion: The application version
*/}}
{{ define "llamacloud.component.temporal.worker" }}
{{- .name | required "You must provide a name for the component." }}
{{- .component | required "You must provide a component for configuration" }}
{{- $appVersion := .appVersion | required "You must provide the Helm Chart AppVersion" }}
{{- $component := .component }}
{{- $component = set $component "prefix" "llamacloud.component.temporal.worker" }}
{{- $component = set $component "name" .name }}
{{- $component = set $component "image" .component.image | default ( print "docker.io/llamaindex/llamacloud-backend:" .appVersion ) }}
{{- $component = set $component "imagePullPolicy" ( .component.imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 8000 }}
{{- $component = set $component "command" (.component.command | default (list "temporal_worker")) }}
{{- $component = set $component "usesS3" "true" }}
{{- $component | toYaml }}
{{- end }}

{{/*
Temporal Worker Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.worker.resources" }}
requests:
  cpu: {{ (((.component).resources).requests).cpu | default "500m" }}
  memory: {{ (((.component).resources).requests).memory | default "4Gi" }}
limits:
  cpu: {{ (((.component).resources).limits).cpu | default "2" }}
  memory: {{ (((.component).resources).limits).memory | default "6Gi" }}
{{- end }}

{{/*
Temporal Worker Liveness Probe.

Parameters:
- component: The component configuration in values.yaml
*/}}
{{ define "llamacloud.component.temporal.worker.livenessProbe" }}
httpGet:
  path: /healthcheck
  port: http
initialDelaySeconds: 30
periodSeconds: 15
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Temporal Worker Readiness Probe.
*/}}
{{ define "llamacloud.component.temporal.worker.readinessProbe" }}
httpGet:
  path: /healthcheck
  port: http
initialDelaySeconds: 30
periodSeconds: 15
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Temporal Worker Startup Probe.
*/}}
{{ define "llamacloud.component.temporal.worker.startupProbe" }}
httpGet:
  path: /healthcheck
  port: http
initialDelaySeconds: 30
periodSeconds: 15
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Temporal Worker Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.worker.env" }}
- name: IS_TEMPORAL_WORKER
  value: "true"
- name: WORKER_HOST
  value: "0.0.0.0"
- name: WORKER_PORT
  value: "8000"
{{- if (.component).extraEnvVariables }}
{{ toYaml (.component).extraEnvVariables }}
{{- end }}
{{- end }}

{{/*
Temporal Worker Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.worker.envFrom" }}
{{- include "llamacloud.secrets.license" .root}}
- configMapRef:
    name: bucket-config
- configMapRef:
    name: common-config
- configMapRef:
    name: extract-config
- configMapRef:
    name: urls-config
- configMapRef:
    name: temporal-connection-config
{{- if (include "llamacloud.component.temporal.worker.configMap" $) }}
- configMapRef:
    name: {{ .component.name | quote }}
{{- end }}
{{- if (include "llamacloud.component.temporal.worker.secret" $) }}
- secretRef:
    name: {{ .component.name | quote }}
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
Temporal Worker Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.worker.secret" }}
{{- end }}

{{/*
Temporal Worker ConfigMap. 

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.worker.configMap" }}
JOB_CONSUMER_PORT: "80"

MAX_JOBS_IN_EXECUTION_PER_JOB_TYPE: {{ ((.root.Values.config).jobs).maxJobsInExecutionPerJobType | default 10 | quote }}
MAX_INDEX_JOBS_IN_EXECUTION: {{ ((.root.Values.config).jobs).maxIndexJobsInExecution | default 0 | quote }}
MAX_DOCUMENT_INGESTION_JOBS_IN_EXECUTION: {{ ((.root.Values.config).jobs).maxDocumentIngestionJobsInExecution | default 1 | quote }}
INCLUDE_JOB_ERROR_DETAILS: {{ ((.root.Values.config).jobs).includeJobErrorDetails | default "true" | quote }}
DEFAULT_TRANSFORM_DOCUMENT_TIMEOUT_SECONDS: {{ ((.root.Values.config).jobs).defaultTransformDocumentTimeoutSeconds | default "240" | quote }}
TRANSFORM_EMBEDDING_CHAR_LIMIT: {{ ((.root.Values.config).jobs).transformEmbeddingCharLimit | default "11520000" | quote }}
{{- end }}

{{/*
Temporal Worker Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.worker.volumeMounts" }}
- mountPath: /tmp
  name: tmp
{{- if (.component).volumeMounts }}
{{ toYaml (.component).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Temporal Worker Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.worker.volumes" }}
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