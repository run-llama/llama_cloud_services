{{- $component := .Values.backend }}

{{/*
Backend Component Settings.
*/}}
{{ define "llamacloud.component.backend" }}
{{- $component := .Values.backend }}
{{- $component = set $component "prefix" "llamacloud.component.backend" }}
{{- $component = set $component "name" "llamacloud" }}
{{- $component = set $component "image" ($.Values.backend).image | default ( print "docker.io/llamaindex/llamacloud-backend:" .Chart.AppVersion ) }}
{{- $component = set $component "imagePullPolicy" ( ($.Values.backend).imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 8000 }}
{{- $component = set $component "command" (list "start_platform_api") }}
{{- $component = set $component "usesS3" "true" }}
{{- $component | toYaml }}
{{- end }}

{{/*
Backend Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.backend.resources" }}
requests:
  cpu: {{ (((.component).resources).requests).cpu | default "500m" }}
  memory: {{ (((.component).resources).requests).memory | default "4Gi" }}
limits:
  cpu: {{ (((.component).resources).limits).cpu | default "2" }}
  memory: {{ (((.component).resources).limits).memory | default "6Gi" }}
{{- end }}

{{/*
Backend Liveness Probe.
*/}}
{{ define "llamacloud.component.backend.livenessProbe" }}
httpGet:
  path: /api/health
  port: http
initialDelaySeconds: 30
periodSeconds: 10
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Backend Readiness Probe.
*/}}
{{ define "llamacloud.component.backend.readinessProbe" }}
httpGet:
  path: /api/health
  port: http
initialDelaySeconds: 30
periodSeconds: 10
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Backend Startup Probe.
*/}}
{{ define "llamacloud.component.backend.startupProbe" }}
httpGet:
  path: /api/health
  port: http
initialDelaySeconds: 30
periodSeconds: 15
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Backend Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.backend.env" }}
{{- if (.component).extraEnvVariables }}
{{ toYaml (.component).extraEnvVariables }}
{{- end }}
{{- end }}

{{/*
Backend Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.backend.envFrom" }}
{{- include "llamacloud.secrets.license" .root }}
- configMapRef:
    name: bucket-config
- configMapRef:
    name: common-config
- configMapRef:
    name: extract-config
- configMapRef:
    name: urls-config
{{- if not .root.Values.temporal.disabled }}
- configMapRef:
    name: temporal-connection-config
{{- end }}
{{- if (include "llamacloud.component.backend.configMap" $) }}
- configMapRef:
    name: {{ .component.name }}
{{- end }}
{{- if (include "llamacloud.component.backend.secret" $) }}
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
Backend Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.backend.secret" }}
{{- end }}

{{/*
Backend ConfigMap. 

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.backend.configMap" }}
{{- end }}

{{/*
Backend Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.backend.volumeMounts" }}
- mountPath: /tmp
  name: tmp
{{- if (.component).volumeMounts }}
{{ toYaml (.component).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Backend Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.backend.volumes" }}
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