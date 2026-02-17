# LlamaCloud Monitoring

LlamaCloud services expose metrics, which are collected by [Prometheus](https://prometheus.io) and visualized in [Grafana](https://grafana.com).

## Prerequisites

To monitor your LlamaCloud deployment, you'll need:

- [Prometheus](https://prometheus.io) - For metrics collection and storage
- [Grafana](https://grafana.com) - For metrics visualization
- [AlertManager](https://prometheus.io/docs/alerting/latest/alertmanager/) - For alert management

These services can be deployed using the [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack) Helm chart.

The kube-prometheus-stack Helm chart provides a complete monitoring solution that includes:

- Prometheus server for metrics collection
- Grafana for visualization with pre-configured dashboards
- AlertManager for handling alerts
- Node exporter for hardware and OS metrics
- kube-state-metrics for Kubernetes object metrics
- Prometheus Operator for managing Prometheus instances

Here is a very basic example of how to deploy the kube-prometheus-stack Helm chart using the `kube-prometheus-stack-example-values.yaml` file located in this directory.

```bash
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack -f kube-prometheus-stack-example-values.yaml
```

For more information about the kube-prometheus-stack Helm chart, please refer to the [kube-prometheus-stack README](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack).

## Metrics

The following services expose metrics:

- `backend`
- `jobsService`
- `jobsWorker`
- `llamaParse`
- `llamaParseOcr`

Metrics are scraped at the `/metrics` endpoint of each service.

To enable metrics for a service, you need to set the `metrics.enabled` parameter to `true` in the service's values.yaml file.

```yaml
# example
backend:
  metrics:
    enabled: true
```

### ServiceMonitors

If using the Prometheus Operator, you can create a ServiceMontior to scrape the metrics from the service. This can be done by adding the following to the `values.yaml` file:

```yaml
# example
backend:
  metrics:
    enabled: true
    serviceMonitor:
      enabled: true
```

## Dashboards

We have a couple of dashboards that are useful for monitoring LlamaCloud. These dashboards are starting points for monitoring your services. For production enviroments, we recommend extending these dashboards to better suit your needs.

- [LlamaCloud Dashboard](./llamacloud-dashboard.json)
- [LlamaParse Dashboard](./llamaparse-dashboard.json)

The above json files can be imported into a Grafana instance. Feel free to refer to the [Grafana documentation](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/import-dashboards/) for more information.

## Prometheus Alerts

Alerting is a crucial part of monitoring your LlamaCloud deployment, especially in production environments. These helm charts support the ability to directly define Prometheus rules in the `values.yaml` file.

```yaml
# example
backend:
  metrics:
    enabled: true
    rules:
      enabled: true
      spec:
        - alert: "Backend is down"
          expr: absent(up{job='backend'})
          for: 1m
          labels:
            severity: "critical"
```
