{{/*
Parse Layout Detection V3 Component Settings.
This is for BYOC deployments using the self-hosted RT-DETRv2 model.
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3" }}
{{- $component := .Values.llamaParseLayoutDetectionApiV3 }}
{{- $component = set $component "prefix" "llamacloud.component.llamaParseLayoutDetectionApiV3" }}
{{- $component = set $component "name" "llamacloud-layout-v3" }}
{{- $component = set $component "image" ($.Values.llamaParseLayoutDetectionApiV3).image | default ( print "docker.io/llamaindex/llamacloud-layout-detection-api-v3:" .Chart.AppVersion ) }}
{{- $component = set $component "imagePullPolicy" ( ($.Values.llamaParseLayoutDetectionApiV3).imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 8000 }}
{{- $component | toYaml }}
{{- end }}

{{/*
Parse Layout Detection V3 Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.resources" }}
requests:
  cpu: {{ (((.component).resources).requests).cpu | default "1" }}
  memory: {{ (((.component).resources).requests).memory | default "8Gi" }}
  {{- if ((.root.Values.config).parseLayoutDetectionV3).gpu }}
  nvidia.com/gpu: 1
  {{- end }}
limits:
  cpu: {{ (((.component).resources).limits).cpu | default "2" }}
  memory: {{ (((.component).resources).limits).memory | default "16Gi" }}
  {{- if ((.root.Values.config).parseLayoutDetectionV3).gpu }}
  nvidia.com/gpu: 1
  {{- end }}
{{- end }}

{{/*
Parse Layout Detection V3 Liveness Probe.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.livenessProbe" }}
httpGet:
  path: /health
  port: http
initialDelaySeconds: 30
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 5
{{- end }}

{{/*
Parse Layout Detection V3 Readiness Probe.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.readinessProbe" }}
httpGet:
  path: /health
  port: http
initialDelaySeconds: 15
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 5
{{- end }}

{{/*
Parse Layout Detection V3 Startup Probe.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.startupProbe" }}
httpGet:
  path: /health
  port: http
initialDelaySeconds: 30
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 10
{{- end }}

{{/*
Parse Layout Detection V3 Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.env" }}
{{- if (.component).extraEnvVariables }}
{{ toYaml (.component).extraEnvVariables }}
{{- end }}
{{- end }}

{{/*
Parse Layout Detection V3 Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.envFrom" }}
{{- include "llamacloud.secrets.license" .root}}
{{- if (include "llamacloud.component.llamaParseLayoutDetectionApiV3.configMap" $) }}
- configMapRef:
    name: {{ .component.name }}
{{- end }}
{{- if (include "llamacloud.component.llamaParseLayoutDetectionApiV3.secret" $) }}
- secretRef:
    name: {{ .component.name }}
{{- end }}
{{- end }}

{{/*
Parse Layout Detection V3 Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.secret" }}
{{- end }}

{{/*
Parse Layout Detection V3 ConfigMap.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.configMap" }}
{{- end }}

{{/*
Parse Layout Detection V3 Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.volumeMounts" }}
- mountPath: /tmp
  name: tmp
{{- if (.component).volumeMounts }}
{{ toYaml (.component).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Parse Layout Detection V3 Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseLayoutDetectionApiV3.volumes" }}
- emptyDir: {}
  name: tmp
{{- if (.component).volumes }}
{{ toYaml (.component).volumes }}
{{- end }}
{{- end }}
