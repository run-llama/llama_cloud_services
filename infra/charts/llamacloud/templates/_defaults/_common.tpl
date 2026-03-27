{{/*
Labels

Parameters:
- name: The name of the component
- root: $
*/}}
{{ define "llamacloud.labels" }}
{{- if .root.Values.commonLabels }}
{{ .root.Values.commonLabels | toYaml }}
{{- end }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
{{- if .name }}
app.kubernetes.io/name: {{ .name | quote }}
{{- end }}
{{- end }}

{{/*
Annotations

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.annotations" }}
{{- range $key, $value := .root.Values.commonAnnotations }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- if .component }}
{{- range $key, $value := .component.annotations }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Pod Annotations

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.podAnnotations" }}
{{- range $key, $value := .root.Values.commonAnnotations }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- if .component }}
{{- range $key, $value := .component.podAnnotations }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Security Context

Parameters:
- component: The component configuration in values.yaml
*/}}
{{ define "llamacloud.podSecurityContext" }}
{{- if not .component.podSecurityContext }}
runAsUser: 1000
runAsGroup: 1000
fsGroup: 1000
seccompProfile:
  type: RuntimeDefault
{{- else }}
{{ toYaml .component.podSecurityContext }}
{{- end }}
{{- end }}

{{/*
Security Context

Parameters:
- component: The component configuration in values.yaml
*/}}
{{ define "llamacloud.securityContext" }}
{{- if not .component.securityContext }}
allowPrivilegeEscalation: false
capabilities:
  drop:
  - all
privileged: false
readOnlyRootFilesystem: true
runAsGroup: 1000
runAsNonRoot: true
runAsUser: 1000
{{- else }}
{{ toYaml .component.securityContext }}
{{- end }}
{{- end }}

{{/*
Activated Components
*/}}
{{- define "llamacloud.components" }}
{{- $activated := dict }}
{{- $activated = set $activated "backend" (include "llamacloud.component.backend" . | fromYaml) }}
{{- $activated = set $activated "jobsService" (include "llamacloud.component.jobsService" . | fromYaml) }}
{{- $activated = set $activated "jobsWorker" (include "llamacloud.component.jobsWorker" . | fromYaml) }}
{{- $activated = set $activated "llamaParse" (include "llamacloud.component.llamaParse" . | fromYaml) }}
{{- $activated = set $activated "usage" (include "llamacloud.component.usage" . | fromYaml) }}
{{- if (($.Values.config).frontend).enabled }}
{{- $activated = set $activated "frontend" (include "llamacloud.component.frontend" . | fromYaml) }}
{{- end }}
{{- if (($.Values.config).parseOcr).enabled }}
{{- $activated = set $activated "llamaParseOcr" (include "llamacloud.component.llamaParseOcr" . | fromYaml) }}
{{- end }}
{{- if (($.Values.config).parseLayoutDetection).enabled }}
{{- $activated = set $activated "llamaParseLayoutDetectionApi" (include "llamacloud.component.llamaParseLayoutDetectionApi" . | fromYaml) }}
{{- end }}
{{- if (($.Values.config).parseLayoutDetectionV3).enabled }}
{{- $activated = set $activated "llamaParseLayoutDetectionApiV3" (include "llamacloud.component.llamaParseLayoutDetectionApiV3" . | fromYaml) }}
{{- end }}
{{- /* Temporal workloads - skip when temporal is disabled */}}
{{- if not $.Values.temporal.disabled }}
{{- $activated = set $activated "temporalJobsService" (include "llamacloud.component.temporal.jobsService" . | fromYaml) }}
{{- $activated = set $activated "temporalLlamaParse" (include "llamacloud.component.temporal.llamaParse" . | fromYaml) }}
{{- range $workerName, $workerConfig := .Values.temporalWorkloads.workers }}
{{- $activated = set $activated $workerName (include "llamacloud.component.temporal.worker" (dict "name" $workerName "component" $workerConfig "appVersion" $.Chart.AppVersion) | fromYaml) }}
{{- end }}
{{- end }}
{{- $activated | toYaml }}
{{- end }}

{{/*
Ingress Scheme
*/}}
{{- define "llamacloud.ingress.scheme" }}http{{ if .Values.ingress.tlsSecretName }}s{{ end }}{{- end }}

{{/*
Renders a complete tree, even values that contains template.
*/}}
{{- define "llamacloud.render" }}
  {{- if typeIs "string" .value }}
    {{- tpl .value .context }}
  {{ else }}
    {{- tpl (.value | toYaml) .context }}
  {{- end }}
{{- end }}