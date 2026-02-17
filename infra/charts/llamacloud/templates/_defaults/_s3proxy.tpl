{{/*
S3Proxy Sidecar Container Definition.
*/}}
{{ define "llamacloud.s3proxy.container" }}
{{- if ((($.Values.config).storageBuckets).s3proxy.enabled | default false) }}
- name: s3proxy
  securityContext: {{ toYaml ((($.Values.config).storageBuckets).s3proxy).securityContext | indent 4}}
  image: "{{ ((($.Values.config).storageBuckets).s3proxy).image | default "docker.io/andrewgaul/s3proxy:sha-82e50ee" }}"
  imagePullPolicy: {{ ((($.Values.config).storageBuckets).s3proxy).imagePullPolicy | default "IfNotPresent" }}
  ports:
  - name: http
    containerPort: {{ print (int ((($.Values.config).storageBuckets).s3proxy.containerPort | default 80))}}
    protocol: TCP
  resources:
    requests:
      cpu: {{ ((((($.Values.config).storageBuckets).s3proxy).resources).requests).cpu | default "500m" }}
      memory: {{ ((((($.Values.config).storageBuckets).s3proxy).resources).requests).memory | default "512Mi" }}
    limits:
      cpu: {{ ((((($.Values.config).storageBuckets).s3proxy).resources).limits).cpu | default "1" }}
      memory: {{ ((((($.Values.config).storageBuckets).s3proxy).resources).limits).memory | default "1Gi" }}
  env:
  - name: LOG_LEVEL
    value: {{ ($.Values.config).logLevel | default "info" }}
  envFrom:
  - configMapRef:
      name: s3proxy-config
  - secretRef:
      name: s3proxy-secret
  volumeMounts:
  - name: s3proxy-tmp
    mountPath: /tmp
    subPath: tmp-dir
{{- end }}
{{- end }}

{{/*
S3Proxy Secret.
*/}}
{{ define "llamacloud.s3proxy.secret" }}
{{- range $key, $value := $.Values.config.storageBuckets.s3proxy.config }}
{{ $key }}: {{ $value | b64enc | quote }}
{{- end }}
{{- end }}

{{/*
S3Proxy ConfigMap Data.
*/}}
{{ define "llamacloud.s3proxy.configMap" }}
S3PROXY_AUTHORIZATION: "none"
S3PROXY_CORS_ALLOW_ORIGINS: "*"
S3PROXY_ENDPOINT: {{ printf "http://0.0.0.0:%d" (int ((($.Values.config).storageBuckets).s3proxy.containerPort | default 80)) | quote }}
S3PROXY_IGNORE_UNKNOWN_HEADERS: "true"
{{- end }}