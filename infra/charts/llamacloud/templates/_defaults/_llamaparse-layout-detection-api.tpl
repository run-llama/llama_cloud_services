{{/*
Parse Layout Detection Component Settings.
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi" }}
{{- $component := .Values.llamaParseLayoutDetectionApi }}
{{- $component = set $component "prefix" "llamacloud.component.llamaParseLayoutDetectionApi" }}
{{- $component = set $component "name" "llamacloud-layout" }}
{{- $component = set $component "image" ($.Values.llamaParseLayoutDetectionApi).image | default ( print "docker.io/llamaindex/llamacloud-layout-detection-api:" .Chart.AppVersion ) }}
{{- $component = set $component "imagePullPolicy" ( ($.Values.llamaParseLayoutDetectionApi).imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 8000 }}
{{- $component | toYaml }}
{{- end }}

{{/*
Parse Layout Detection Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.resources" }}
requests:
  cpu: {{ (((.component).resources).requests).cpu | default "1" }}
  memory: {{ (((.component).resources).requests).memory | default "6Gi" }}
  {{- if ((.root.Values.config).parseLayoutDetection).gpu }}
  nvidia.com/gpu: 1
  {{- end }}
limits:
  cpu: {{ (((.component).resources).limits).cpu | default "2" }}
  memory: {{ (((.component).resources).limits).memory | default "12Gi" }}
  {{- if ((.root.Values.config).parseLayoutDetection).gpu }}
  nvidia.com/gpu: 1
  {{- end }}
{{- end }}

{{/*
Parse Layout Detection Liveness Probe.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.livenessProbe" }}
httpGet:
  path: /health
  port: http
initialDelaySeconds: 10
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 5
{{- end }}

{{/*
Parse Layout Detection Readiness Probe.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.readinessProbe" }}
httpGet:
  path: /health
  port: http
initialDelaySeconds: 10
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 5
{{- end }}

{{/*
Parse Layout Detection Startup Probe.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.startupProbe" }}
httpGet:
  path: /health
  port: http
initialDelaySeconds: 10
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 5
{{- end }}

{{/*
Parse Layout Detection Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.env" }}
{{- if (.component).extraEnvVariables }}
{{ toYaml (.component).extraEnvVariables }}
{{- end }}
{{- end }}

{{/*
Parse Layout Detection Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.envFrom" }}
{{- include "llamacloud.secrets.license" .root}}
{{- if (include "llamacloud.component.llamaParseLayoutDetectionApi.configMap" $) }}
- configMapRef:
    name: {{ .component.name }}
{{- end }}
{{- if (include "llamacloud.component.llamaParseLayoutDetectionApi.secret" $) }}
- secretRef:
    name: {{ .component.name }}
{{- end }}
{{- end }}

{{/*
Parse Layout Detection Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.secret" }}
{{- end }}

{{/*
Parse Layout Detection ConfigMap. 

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.configMap" }}
{{- end }}

{{/*
Parse Layout Detection Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.volumeMounts" }}
- mountPath: /tmp
  name: tmp
{{- if (.component).volumeMounts }}
{{ toYaml (.component).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Parse Layout Detection Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApi.volumes" }}
- emptyDir: {}
  name: tmp
{{- if (.component).volumes }}
{{ toYaml (.component).volumes }}
{{- end }}
{{- end }}