{{/*
Usage Component Settings.
*/}}
{{ define "llamacloud.component.usage" }}
{{- $component := .Values.usage }}
{{- $component = set $component "prefix" "llamacloud.component.usage" }}
{{- $component = set $component "name" "llamacloud-telemetry" }}
{{- $component = set $component "image" ($.Values.usage).image | default ( print "docker.io/llamaindex/llamacloud-backend:" .Chart.AppVersion ) }}
{{- $component = set $component "imagePullPolicy" ( ($.Values.usage).imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 8005 }}
{{- $component = set $component "command" (list "start_usage_service") }}
{{- $component | toYaml }}
{{- end }}

{{/*
Usage Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.usage.resources" }}
requests:
  cpu: {{ (((.root.Values.usage).resources).requests).cpu | default "1" }}
  memory: {{ (((.root.Values.usage).resources).requests).memory | default "1Gi" }}
limits:
  cpu: {{ (((.root.Values.usage).resources).limits).cpu | default "2" }}
  memory: {{ (((.root.Values.usage).resources).limits).memory | default "2Gi" }}
{{- end }}

{{/*
Usage Liveness Probe.
*/}}
{{ define "llamacloud.component.usage.livenessProbe" }}
httpGet:
  path: /health_check
  port: http
initialDelaySeconds: 15
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Usage Readiness Probe.
*/}}
{{ define "llamacloud.component.usage.readinessProbe" }}
httpGet:
  path: /health_check
  port: http
initialDelaySeconds: 15
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Usage Startup Probe.
*/}}
{{ define "llamacloud.component.usage.startupProbe" }}
httpGet:
  path: /health_check
  port: http
initialDelaySeconds: 15
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Usage Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.usage.env" }}
{{- if (.root.Values.usage).extraEnvVariables }}
{{ toYaml (.root.Values.usage).extraEnvVariables }}
{{- end }}
{{- end }}


{{/*
Usage Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.usage.envFrom" }}
{{- include "llamacloud.secrets.license" .root}}
{{- if (include "llamacloud.component.usage.configMap" $) }}
- configMapRef:
    name: {{ .component.name }}
{{- end }}
{{- if (include "llamacloud.component.usage.secret" $) }}
- secretRef:
    name: {{ .component.name }}
{{- end }}
{{- include "llamacloud.secrets.postgresql" .root }}
{{- include "llamacloud.secrets.redis" .root }}
{{- end }}

{{/*
Usage Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.usage.secret" }}
{{- end }}

{{/*
Usage ConfigMap.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.usage.configMap" }}
{{- end }}

{{/*
Usage Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.usage.volumeMounts" }}
- mountPath: /tmp
  name: tmp
{{- if (.root.Values.usage).volumeMounts }}
{{ toYaml (.root.Values.usage).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Usage Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.usage.volumes" }}
- emptyDir: {}
  name: tmp
{{- if (.root.Values.usage).volumes }}
{{ toYaml (.root.Values.usage).volumes }}
{{- end }}
{{- end }}