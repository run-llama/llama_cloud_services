{{/*
Frontend Component Settings.
*/}}
{{ define "llamacloud.component.frontend" }}
{{- $component := .Values.frontend }}
{{- $component = set $component "prefix" "llamacloud.component.frontend" }}
{{- $component = set $component "name" "llamacloud-web" }}
{{- $component = set $component "image" ( ($.Values.frontend).image | default ( print "docker.io/llamaindex/llamacloud-frontend:" .Chart.AppVersion ) ) }}
{{- $component = set $component "imagePullPolicy" ( ($.Values.frontend).imagePullPolicy | default "IfNotPresent" ) }}
{{- $component = set $component "port" 3000 }}
{{- $component | toYaml }}
{{- end }}

{{/*
Frontend Resources.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.frontend.resources" }}
requests:
  cpu: {{ (((.component).resources).requests).cpu | default "500m" }}
  memory: {{ (((.component).resources).requests).memory | default "512Mi" }}
limits:
  cpu: {{ (((.component).resources).limits).cpu | default "1" }}
  memory: {{ (((.component).resources).limits).memory | default "1Gi" }}
{{- end }}

{{/*
Frontend Liveness Probe.
*/}}
{{ define "llamacloud.component.frontend.livenessProbe" }}
httpGet:
  path: /api/healthz
  port: http
initialDelaySeconds: 30
periodSeconds: 10
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Frontend Readiness Probe.
*/}}
{{ define "llamacloud.component.frontend.readinessProbe" }}
httpGet:
  path: /api/healthz
  port: http
initialDelaySeconds: 30
periodSeconds: 10
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Frontend Startup Probe.
*/}}
{{ define "llamacloud.component.frontend.startupProbe" }}
httpGet:
  path: /api/healthz
  port: http
initialDelaySeconds: 30
periodSeconds: 15
timeoutSeconds: 5
failureThreshold: 30
{{- end }}

{{/*
Frontend Environment Variables.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.frontend.env" }}
{{- if (.component).extraEnvVariables }}
{{ toYaml (.component).extraEnvVariables }}
{{- end }}
{{- end }}

{{/*
Frontend Environment Variables from Secrets and ConfigMaps.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.frontend.envFrom" }}
{{- include "llamacloud.secrets.license" .root}}
- configMapRef:
    name: urls-config
{{- if (include "llamacloud.component.frontend.configMap" $) }}
- configMapRef:
    name: {{ .component.name }}
{{- end }}
{{- if (include "llamacloud.component.frontend.secret" $) }}
- secretRef:
    name: {{ .component.name }}
{{- end }}
{{- end }}

{{/*
Frontend Secret.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.frontend.secret" }}
{{- end }}

{{/*
Frontend ConfigMap.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.frontend.configMap" }}
HOSTNAME: 0.0.0.0
{{- if (.root.Values.qdrant).enabled }}
NEXT_PUBLIC_BYOC_HAS_MANAGED_QDRANT: "true"
{{- end }}
{{- end }}

{{/*
Frontend Volume Mounts.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.frontend.volumeMounts" }}
- mountPath: /tmp
  name: tmp
- mountPath: /.next/cache
  name: nextjs-cache
- mountPath: /app/frontend/.next/cache
  name: local-nextjs-cache
{{- if (.component).volumeMounts }}
{{ toYaml (.component).volumeMounts }}
{{- end }}
{{- end }}

{{/*
Frontend Volumes.

Parameters:
- component: The component configuration in values.yaml
- root: $
*/}}
{{ define "llamacloud.component.frontend.volumes" }}
- emptyDir: {}
  name: tmp
- emptyDir: {}
  name: nextjs-cache
- emptyDir: {}
  name: local-nextjs-cache
{{- if (.component).volumes }}
{{ toYaml (.component).volumes }}
{{- end }}
{{- end }}