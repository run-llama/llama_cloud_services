{{/*
Temporal Jobs Service Component Settings.
*/}}
{{ define "llamacloud.component.temporal.jobsService" }}
{{- $component := ($.Values.temporalWorkloads).jobsService }}
{{- $component = set $component "prefix" "llamacloud.component.temporal.jobsService" }}
{{- $component = set $component "name" "llamacloud-temporal-operator" }}
{{- $component = set $component "image" (($.Values.temporalWorkloads).jobsService).image | default ( print "docker.io/llamaindex/llamacloud-backend:" .Chart.AppVersion ) }}
{{- $component = set $component "imagePullPolicy" ( (($.Values.temporalWorkloads).jobsService).imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 8002 }}
{{- $component = set $component "command" (list "start_jobs_api") }}
{{- $component = set $component "usesS3" "true" }}
{{- $component | toYaml }}
{{- end }}

{{/*
Temporal Jobs Service Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.jobsService.resources" }}
requests:
  cpu: {{ (((.component).resources).requests).cpu | default "500m" }}
  memory: {{ (((.component).resources).requests).memory | default "4Gi" }}
limits:
  cpu: {{ (((.component).resources).limits).cpu | default "2" }}
  memory: {{ (((.component).resources).limits).memory | default "8Gi" }}
{{- end }}

{{/*
Temporal Jobs Service Liveness Probe.
*/}}
{{ define "llamacloud.component.temporal.jobsService.livenessProbe" }}
httpGet:
  path: /healthcheck
  port: http
periodSeconds: 15
timeoutSeconds: 10
failureThreshold: 30
{{- end }}

{{/*
Temporal Jobs Service Readiness Probe.
*/}}
{{ define "llamacloud.component.temporal.jobsService.readinessProbe" }}
httpGet:
  path: /healthcheck
  port: http
periodSeconds: 15
timeoutSeconds: 10
failureThreshold: 30
{{- end }}

{{/*
Temporal Jobs Service Startup Probe.
*/}}
{{ define "llamacloud.component.temporal.jobsService.startupProbe" }}
httpGet:
  path: /healthcheck
  port: http 
initialDelaySeconds: 30
periodSeconds: 15
timeoutSeconds: 10
failureThreshold: 30
{{- end }}

{{/*
Temporal Jobs Service Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.jobsService.env" }}
{{- if (.component).extraEnvVariables }}
{{ toYaml (.component).extraEnvVariables }}
{{- end }}
{{- end }}

{{/*
Temporal Jobs Service Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.jobsService.envFrom" }}
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
{{- if (include "llamacloud.component.temporal.jobsService.configMap" $) }}
- configMapRef:
    name: {{ .component.name }}
{{- end }}
{{- if (include "llamacloud.component.temporal.jobsService.secret" $) }}
- secretRef:
    name: {{ .component.name }}
{{- end }}
- secretRef:
    name: bucket-secret
{{- include "llamacloud.secrets.postgresql" .root }}
{{- include "llamacloud.secrets.mongodb" .root }}
{{- include "llamacloud.secrets.rabbitmq" .root }}
{{- include "llamacloud.secrets.redis" .root }}
{{- include "llamacloud.secrets.openAi" .root }}
{{- include "llamacloud.secrets.anthropic" .root }}
{{- include "llamacloud.secrets.gemini" .root }}
{{- include "llamacloud.secrets.azureOpenAi" .root }}
{{- include "llamacloud.secrets.awsBedrock" .root }}
{{- include "llamacloud.secrets.googleVertexAi" .root }}
{{- end }}

{{/*
Temporal Jobs Service Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.jobsService.secret" }}
{{- end }}

{{/*
Temporal Jobs Service ConfigMap. 

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.jobsService.configMap" }}
{{- end }}

{{/*
Temporal Jobs Service Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.jobsService.volumeMounts" }}
- mountPath: /tmp
  name: tmp
{{- if (.component).volumeMounts }}
{{ toYaml (.component).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Temporal Jobs Service Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.temporal.jobsService.volumes" }}
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