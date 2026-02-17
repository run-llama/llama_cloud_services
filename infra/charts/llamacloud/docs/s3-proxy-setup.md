# Deploying LlamaCloud with S3Proxy

The LlamaCloud Helm Chart supports the service [s3proxy](https://github.com/gaul/s3proxy) as a way to connect LlamaCloud services to different cloud filestores. There are a few ways to configure this service in the charts. The following examples will show you how to configure s3proxy to proxy to AWS S3 requests to the Azure Blob Storage.

## 1. Configure directly in the values.yaml

Inside the `values.yaml`, there is a field, `.Values.s3proxy.config`, where you can provide the configurations directly.

```yaml
s3proxy:
  enabled: true

  config:
    S3PROXY_ENDPOINT: "http://0.0.0.0:80"
    S3PROXY_AUTHORIZATION: "none"
    JCLOUDS_PROVIDER: "azureblob"
    JCLOUDS_AZUREBLOB_AUTH: "azureKey"
    JCLOUD_REGION: "<azure-region>"
    JCLOUDS_IDENTITY: "<azure-storage-account-name>"
    JCLOUDS_CREDENTIAL: "<azure-storage-account-key>"
    JCLOUDS_ENDPOINT: "<azure-storage-account-endpoint>"

```

## 2. Use an existing secret or configmap

The `values.yaml` provides a way to pass in an existing secret or configmap with the necessary configuration

```yaml
# existing-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: existing-s3proxy-secret
data:
  S3PROXY_ENDPOINT: "http://0.0.0.0:80"
  S3PROXY_AUTHORIZATION: "none"
  JCLOUDS_PROVIDER: "azureblob"
  JCLOUDS_AZUREBLOB_AUTH: "azureKey"
  JCLOUD_REGION: "<azure-region>"
  JCLOUDS_IDENTITY: "<azure-storage-account-name>"
  JCLOUDS_CREDENTIAL: "<azure-storage-account-key>"
  JCLOUDS_ENDPOINT: "<azure-storage-account-endpoint>"
  

# values.yaml
s3proxy:
  enabled: true

  envFromSecretName: existing-s3proxy-secret
```

## 3. Configure extra environment variables

The `values.yaml` also supports an `extraEnvVariables` field that adds envariable variable configuration to the s3proxy Deployment object.

```yaml
# values.yaml
s3proxy:
  enabled: true

  extraEnvVariables:
  - name: S3PROXY_ENDPOINT
    value: "http://0.0.0.0:80"
  - name: JCLOUDS_CREDENTIAL
    valueFrom:
      secretKeyRef:
        name: azure-secret
        key: storage-account-key
  - name: OTHER_VARIABLES
    value: "other values"
```

## Documentation

For more information, please refer to the following:

- [S3 Proxy Config Examples](https://github.com/gaul/s3proxy/wiki/Storage-backend-examples)
- [Dockerfile with Env Vars](https://github.com/gaul/s3proxy/blob/master/Dockerfile)
