{{/*
Parse Component Settings.
*/}}
{{ define "llamacloud.component.llamaParse" }}
{{- $component := .Values.llamaParse }}
{{- $component = set $component "prefix" "llamacloud.component.llamaParse" }}
{{- $component = set $component "name" "llamacloud-parse" }}
{{- $component = set $component "image" ($.Values.llamaParse).image | default ( print "docker.io/llamaindex/llamacloud-llamaparse:" .Chart.AppVersion ) }}
{{- $component = set $component "imagePullPolicy" ( ($.Values.llamaParse).imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 8004 }}
{{- $component = set $component "usesS3" "true" }}
{{- $component | toYaml }}
{{- end }}

{{/*
Parse Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParse.resources" }}
requests:
  cpu: {{ (((.component).resources).requests).cpu | default "3" }}
  memory: {{ (((.component).resources).requests).memory | default "6Gi" }}
limits:
  cpu: {{ (((.component).resources).limits).cpu | default "7" }}
  memory: {{ (((.component).resources).limits).memory | default "13Gi" }}
{{- end }}

{{/*
Parse Liveness Probe.
*/}}
{{ define "llamacloud.component.llamaParse.livenessProbe" }}
httpGet:
  path: /livez
  port: http
initialDelaySeconds: 30
periodSeconds: 30
timeoutSeconds: 5
failureThreshold: 10
{{- end }}

{{/*
Parse Readiness Probe.
*/}}
{{ define "llamacloud.component.llamaParse.readinessProbe" }}
httpGet:
  path: /livez
  port: http
initialDelaySeconds: 30
periodSeconds: 30
timeoutSeconds: 5
failureThreshold: 10
{{- end }}

{{/*
Parse Startup Probe.
*/}}
{{ define "llamacloud.component.llamaParse.startupProbe" }}
httpGet:
  path: /livez
  port: http
initialDelaySeconds: 30
periodSeconds: 30
timeoutSeconds: 5
failureThreshold: 10
{{- end }}

{{/*
Parse Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParse.env" }}
{{- if (.component).extraEnvVariables }}
{{ toYaml (.component).extraEnvVariables }}
{{- end }}
{{- end }}

{{/*
Parse Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParse.envFrom" }}
{{- include "llamacloud.secrets.license" .root}}
- configMapRef:
    name: bucket-config
- configMapRef:
    name: urls-config
- configMapRef:
    name: concurrency-config
{{- if (include "llamacloud.component.llamaParse.configMap" $ ) }}
- configMapRef:
    name: {{ .component.name }}
{{- end }}
{{- if (include "llamacloud.component.llamaParse.secret" $) }}
- secretRef:
    name: {{ .component.name }}
{{- end }}
- secretRef:
    name: bucket-secret
{{- include "llamacloud.secrets.rabbitmq" .root }}
{{- include "llamacloud.secrets.openAi" .root }}
{{- include "llamacloud.secrets.anthropic" .root }}
{{- include "llamacloud.secrets.gemini" .root }}
{{- include "llamacloud.secrets.azureOpenAi" .root }}
{{- include "llamacloud.secrets.awsBedrock" .root }}
{{- include "llamacloud.secrets.googleVertexAi" .root }}
{{- end }}

{{/*
Parse Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParse.secret" }}
{{- end }}

{{/*
Parse ConfigMap. 

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParse.configMap" }}
DEBUG_MODE: {{ ((.root.Values.config).parse).debugMode | default false | quote }}
MAX_QUEUE_CONCURRENCY: {{ ((.root.Values.config).parse).maxQueueConcurrency | default 1 | quote }}

{{- if ((.root.Values.config).parse).preferedPremiumModel }}
PREFERED_PREMIUM_MODE_MODEL: {{ ((.root.Values.config).parse).preferedPremiumModel | quote }}
{{- end }}
{{if ((.root.Values.config).parse).writeDirectory }}
LLAMAPARSE_WRITE_DIRECTORY: {{ ((.root.Values.config).parse).writeDirectory | quote }}
{{- end }}
{{- end }}

{{/*
Parse Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParse.volumeMounts" }}
- mountPath: /tmp
  name: tmp
{{- if (.component).volumeMounts }}
{{ toYaml (.component).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Parse Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParse.volumes" }}
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