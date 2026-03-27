# Helm Chart Downgrade Runbook

Upgrading this helm chart is the same as upgrading any helm chart:
```shell
helm -n <namespace> upgrade llamacloud llamaindex/llamacloud -f values.yaml --version <chart-version>
```

However, an extra step would be required for *downgrades*. This is primarly because the postgres database schemas will need to be migrated back to the versions they were at in the helm chart you are aiming to downgrade to.
At a high level, you will first need to run this alembic downgrade within your deployment pod before being able to run the full helm-chart downgrade.

For this, we've provided a utility script in this repo named [`helm_chart_alembic_version.sh`](../scripts/helm_chart_alembic_version.sh). Each helm chart is on a specific alembic migration version which indicates the state of the postgres database schema at the point in time the specific helm chart version was created.
This script will simply print out this alembic migration version for a given helm chart version. Here are the steps to use this when performing a helm chart downgrade:
1. Determine which helm chart version you would like to downgrade to
    - Consult our [CHANGELOG](../CHANGELOG.md) to see the changes in each version.
1. Run the [`helm_chart_alembic_version.sh`](../scripts/helm_chart_alembic_version.sh) script with the helm-chart version you are downgrading to
    - Usage: `./scripts/helm_chart_alembic_version.sh <version you are downgrading to>`
        - e.g. `./scripts/helm_chart_alembic_version.sh 0.1.47` should print a alembic version of `f43d21f9cdb8`
    - This script may take a minute or two to finish
    - Copy/save the alembic version that is printed at the end of this script
1. Run the downgrade command on the backend pod
    - Assuming the helm chart is deployed in a namespace named `llamacloud`, here are some commands for doing this:
        - List the pods: `kubectl get po -n llamacloud`
        - In the list of pods, find a pod whose name starts with `llamacloud-backend-` and copy its name
        - Run the downgrade command: `kubectl exec -n llamacloud -it <copied pod name> -- alembic downgrade <alembic version copied in prior step>`
            - e.g. `kubectl exec -n llamacloud -it llamacloud-backend-58b75b89c6-74847 -- alembic downgrade f43d21f9cdb8`
            - **NOTE:** This command will have the likely outcome of causing a partial loss of functionality in your LlamaCloud deployment and data-loss for any tables/columns that are dropped as part of this DB schema downgrade.
1. Downgrade the helm-chart to the your target helm chart version: `helm -n <namespace> upgrade llamacloud llamaindex/llamacloud -f values.yaml --version <chart-version>`

You should now see that the deployment to the downgraded helm chart version completes succesfully.
