# gcloud reference

## Get environment information

Command to get the configuration of the environment:

```
gcloud composer environments describe {env-name} --project={env-project} --location={env-region} --format=yaml
```

## List files in the environment's bucket

Command to list the contents of `dags/` directory in the environment's bucket:

```
DAGS_FOLDER=$(gcloud composer environments describe {env-name} --project={env-project} --location={env-region} --format="value(config.dagGcsPrefix)")
gcloud storage ls $DAGS_FOLDER
```

## Fetch environment logs

Command to fetch log entries from Cloud Logging:

```
gcloud logging read {filter} --limit=50 --format="yaml(logName,severity,labels,textPayload,timestamp)"
```

**How to build the filter:**

1.  ALWAYS include these conditions:

```
resource.type="cloud_composer_environment" AND
resource.labels.project_id={env-project} AND
resource.labels.location={env-region} AND
resource.labels.environment_name={env-name}
```

2.  Optionally include `AND logName={log-name}` to fetch logs of a specific
    component. `log-name` is one of:

    -   `projects/{env-project}/logs/airflow-scheduler`
    -   `projects/{env-project}/logs/airflow-triggerer`
    -   `projects/{env-project}/logs/airflow-webserver`
    -   `projects/{env-project}/logs/airflow-worker`
    -   `projects/{env-project}/logs/airflow-k8s-operator`
    -   `projects/{env-project}/logs/airflow-k8s-worker`
    -   `projects/{env-project}/logs/dag-processor-manager`
    -   `projects/{env-project}/logs/db-retention`
    -   `projects/{env-project}/logs/build-log`

3.  Optionally include condition like `AND timestamp <= "2026-01-01T00:00:00Z"`
    to fetch logs from a specific timeframe.
