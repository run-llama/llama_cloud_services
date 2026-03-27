{{/*
Parse OCR Image Tag Suffix.
*/}}
{{ define "llamacloud.component.llamaParseOcr.imageTagSuffix" }}
{{- if not ((.Values.config).parseOcr).gpu -}}
-cpu
{{- end }}
{{- end }}

{{/*
Parse OCR Component Settings.
*/}}
{{ define "llamacloud.component.llamaParseOcr" }}
{{- $suffix := include "llamacloud.component.llamaParseOcr.imageTagSuffix" . }}
{{- $component := .Values.llamaParseOcr | deepCopy }}
{{- $component = set $component "prefix" "llamacloud.component.llamaParseOcr" }}
{{- $component = set $component "name" "llamacloud-ocr" }}
{{- if not (empty ($.Values.llamaParseOcr).image) }}
{{- $component = set $component "image" (print ($.Values.llamaParseOcr).image $suffix) }}
{{- else }}
{{- $component = set $component "image" ( print "docker.io/llamaindex/llamacloud-llamaparse-ocr:" .Chart.AppVersion $suffix ) }}
{{- end }}
{{- $component = set $component "imagePullPolicy" ( ($.Values.llamaParseOcr).imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 8080 }}
{{- $component = set $component "command" (list "serve") }}
{{- $component | toYaml }}
{{- end }}

{{/*
Parse OCR Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseOcr.resources" }}
requests:
  cpu: {{ (((.component).resources).requests).cpu | default "2" }}
  memory: {{ (((.component).resources).requests).memory | default "12Gi" }}
  {{- if ((.root.Values.config).parseOcr).gpu }}
  nvidia.com/gpu: 1
  {{- end }}
limits:
  cpu: {{ (((.component).resources).limits).cpu | default "4" }}
  memory: {{ (((.component).resources).limits).memory | default "16Gi" }}
  {{- if ((.root.Values.config).parseOcr).gpu }}
  nvidia.com/gpu: 1
  {{- end }}
{{- end }}

{{/*
Parse OCR Liveness Probe.
*/}}
{{ define "llamacloud.component.llamaParseOcr.livenessProbe" }}
httpGet:
  path: /health_check
  port: http
initialDelaySeconds: 10
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 5
{{- end }}

{{/*
Parse OCR Readiness Probe.
*/}}
{{ define "llamacloud.component.llamaParseOcr.readinessProbe" }}
httpGet:
  path: /health_check
  port: http
initialDelaySeconds: 10
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 5
{{- end }}

{{/*
Parse OCR Startup Probe.
*/}}
{{ define "llamacloud.component.llamaParseOcr.startupProbe" }}
httpGet:
  path: /health_check
  port: http
initialDelaySeconds: 10
periodSeconds: 15
successThreshold: 1
timeoutSeconds: 5
failureThreshold: 5
{{- end }}

{{/*
Parse OCR Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseOcr.env" }}
{{- if ((.root.Values.config).parseOcr).gpu }}
- name: PADDLE_OCR_ENABLED
  value: "true"
{{- end }}
{{- if (.component).extraEnvVariables }}
{{ toYaml (.component).extraEnvVariables }}
{{- end }}
{{- end }}

{{/*
Parse OCR Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseOcr.envFrom" }}
{{- include "llamacloud.secrets.license" .root}}
{{- if (include "llamacloud.component.llamaParseOcr.configMap" $) }}
- configMapRef:
    name: {{ .component.name }}
{{- end }}
{{- if (include "llamacloud.component.llamaParseOcr.secret" $) }}
- secretRef:
    name: {{ .component.name }}
{{- end }}
{{- end }}

{{/*
Parse OCR Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseOcr.secret" }}
{{- end }}

{{/*
Parse OCR ConfigMap. 

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseOcr.configMap" }}
{{- end }}

{{/*
Parse OCR Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseOcr.volumeMounts" }}
- mountPath: /tmp
  name: tmp
{{- if (.component).volumeMounts }}
{{ toYaml (.component).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Parse OCR Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.llamaParseOcr.volumes" }}
- emptyDir: {}
  name: tmp
{{- if (.component).volumes }}
{{ toYaml (.component).volumes }}
{{- end }}
{{- end }}