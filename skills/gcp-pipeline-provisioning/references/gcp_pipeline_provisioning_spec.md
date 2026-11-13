```yaml
environments:
  dev:
    project: {{ project }}
    region: {{ region }}
    variables:
      REPO_NAME: my-repo
      SERVICE_ACCOUNT_EMAIL: "[NAME]@{{ project }}.iam.gserviceaccount.com"
    secrets:
      YOUR_SECRET_NAME: "projects/{{ project }}/secrets/your-secret/versions/latest"
    resources:
      # --- BigQuery ---
      - type: bigquery.dataset
        name: my_dataset
        definition:
          labels:
            env: dev
            datacloud: __REQUIRED_LABEL__
      - type: bigquery.table
        name: my_table
        parent: my_dataset
        definition:
          schema:
            fields:
              - name: id
                type: STRING
              - name: value
                type: INTEGER
          labels:
            env: dev
            datacloud: __REQUIRED_LABEL__
      - type: bigquerydatatransfer.transferConfig
        name: my_dts_config
        metadata:
          serviceAccountName: "{{ SERVICE_ACCOUNT_EMAIL }}"
        definition:
          displayName: "My Secured DTS Config"
          dataSourceId: some_external_datasource
          schedule: "every 24 hours"
          destinationDatasetId: my_dataset
          params:
            api_key_or_password: "{{ YOUR_SECRET_NAME }}"
            other_param: "value"

      # --- Dataform ---
      - type: dataform.repository
        name: {{ REPO_NAME }}
        definition:
          labels:
            env: dev
            datacloud: __REQUIRED_LABEL__
      - type: dataform.repository.releaseConfig
        name: my-release-config
        parent: {{ REPO_NAME }}
        definition:
          gitCommitish: {{ COMMIT_SHA }}
          codeCompilationConfig:
            defaultDatabase: "{{ project }}"
      - type: dataform.repository.workflowConfig
        name: my-workflow-config
        parent: {{ REPO_NAME }}
        definition:
          releaseConfig: "my-release-config"
          invocationConfig:
            includedTags: ["daily"]
            transitiveDependenciesIncluded: true
            serviceAccount: dataform-sa@{{ project_number }}.iam.gserviceaccount.com
          cronSchedule: "0 0 * * *"
          timeZone: "America/Los_Angeles"
      - type: dataform.repository.workspace
        name: my-workspace
        parent: {{ REPO_NAME }}
        definition: {}

      # --- Dataproc ---
      - type: dataproc.cluster
        name: my-dataproc-cluster
        definition:
          config:
            masterConfig:
              numInstances: 1
              machineTypeUri: n1-standard-4
            workerConfig:
              numInstances: 2
              machineTypeUri: n1-standard-4
      - type: dataproc.autoscalingPolicy
        name: my-autoscaling-policy
        definition:
          workerConfig:
            minInstances: 2
            maxInstances: 10
          basicAlgorithm:
            yarnConfig:
              gracefulDecommissionTimeout: 0s
              scaleUpFactor: 1.0
      - type: dataproc.workflowTemplate
        name: my-workflow-template
        definition:
          placement:
            managedCluster:
              clusterName: my-dataproc-cluster
          jobs:
            - stepId: my-spark-job
              sparkJob:
                mainClass: org.apache.spark.examples.SparkPi
                jarFileUris: ["file:///usr/lib/spark/examples/jars/spark-examples.jar"]

```
