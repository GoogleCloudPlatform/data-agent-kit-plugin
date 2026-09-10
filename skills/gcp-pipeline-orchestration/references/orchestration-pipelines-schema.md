# Pipeline YAML Schema
Defines the orchestration pipelines schema using Protocol Buffers.
Source of truth for schema: https://github.com/GoogleCloudPlatform/orchestration-pipelines/blob/main/orchestration_pipelines_models/pipeline_v1_model/protos/orchestration_pipeline.proto

Field names in YAML should generally be camelCase (e.g., use `pipelineId` for the proto field `pipeline_id`).
However, fields of type `Struct` which represent configuration objects for other systems (e.g., `cluster_config`, `environment_config`, `job`, `workflow_invocation`) must use snake_case in YAML.
## Syntax
/////////////////////////
// Pipeline Models (YAML fields)
////////////////////////
message OrchestrationPipeline {
  string model_version = 1 [(pipeline_models.validation.is_required) = true];
  string pipeline_id = 2 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  string description = 3;
  PipelineRunner runner = 4 [(pipeline_models.validation.disallow_zero_enum) = true];
  string owner = 5 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_#-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 32
  ];
  Defaults defaults = 6 [(pipeline_models.validation.is_required) = true];
  repeated Trigger triggers = 7; // Can be empty.
  repeated Action actions = 8 [(pipeline_models.validation.min_items) = 1];
  // Validation for items in repeated fields (e.g. regex for each tag) is not
  // supported by field options and should be handled in custom logic.
  // Each tag should match: ^[a-zA-Z0-9_-]{1,32}$
  repeated string tags = 9; // Can be empty.
  Notification notifications = 10;
}

enum PipelineRunner {
  pipeline_runner_undefined = 0;
  airflow = 1;
}

enum TriggerRule {
  trigger_rule_undefined = 0;
  all_success = 1;
  all_failed = 2;
  all_done = 3;
  one_failed = 4;
  one_success = 5;
  always = 6;
}

message Defaults {
  string project_id = 1 [(pipeline_models.validation.is_required) = true];
  string location = 2 [(pipeline_models.validation.is_required) = true];
  ExecutionConfig execution_config = 3 [(pipeline_models.validation.is_required) = true];
}

message ExecutionConfig {
  // Per proto3 design, scalar fields like int32 have a default value (0) and
  // cannot be truly 'required'. The `min_value` option is used instead.
  int32 retries = 1 [(pipeline_models.validation.min_value) = 0];
}

message OnPipelineFailure {
  repeated string email = 1;
}

message Notification {
  OnPipelineFailure on_pipeline_failure = 1;
}

/////////////////////////
// Triggers
////////////////////////
message ScheduleTrigger {
  string interval = 1 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.is_cron_expression) = true
  ];
  string start_time = 2 [(pipeline_models.validation.is_required) = true, (pipeline_models.validation.is_iso8601_timestamp) = true];
  // Cross-field validation (e.g. end_time > start_time) should be handled
  // in custom validation logic.
  string end_time = 3 [(pipeline_models.validation.is_iso8601_timestamp) = true];
  bool catchup = 4; // Default: false.
  string timezone = 5 [(pipeline_models.validation.is_iana_timezone) = true]; // Defaults to "UTC" if not provided.
}

message Trigger {
  // NOTE: YAML mapping for oneof:
  // triggers:
  //   - schedule: { ... }
  oneof trigger {
    ScheduleTrigger schedule = 1;
  }
}

/////////////////////////
// Engines
////////////////////////
message LocalEngine {
}

message BigQueryEngine {
  // Location of the BigQuery dataset / job execution (e.g., "US", "EU", "us-central1").
  // If not specified, falls back to defaults.location. Must match the dataset's region or multi-region.
  string location = 1;
  // Destination table (e.g., "project.dataset.table_name").
  // When destination_table is set, the SQL query must be a pure SELECT statement without DDL (no CREATE TABLE).
  string destination_table = 2;
  repeated string impersonation_chain = 3;
}

// For Dataproc on GCE, you MUST set either existing_cluster or ephemeral_cluster in YAML.
//
// Example (Existing):
//   dataprocOnGce:
//     existingCluster:
//       clusterName: "my-cluster"
//
// Example (Ephemeral):
//   dataprocOnGce:
//     ephemeralCluster:
//       clusterName: "temp-cluster"
//       resourceProfile:
//         path: "cluster_profile.json"
message DataprocOnGceEngine {
  oneof config {
    DataprocExistingClusterConfiguration existing_cluster = 1;
    DataprocEphemeralConfiguration ephemeral_cluster = 2;
  }
}

message DataprocExistingClusterConfiguration {
  string cluster_name = 1 [(pipeline_models.validation.is_required) = true];
  string location = 2;
  string project_id = 3;
  repeated string impersonation_chain = 4;
  // Optional field for standard Spark properties.
  // Those properties will be used to run a job on existing cluster.
  // See https://spark.apache.org/docs/latest/configuration.html for details
  map<string, string> properties = 5;
}

message DataprocEphemeralConfiguration {
  string cluster_name = 1 [(pipeline_models.validation.is_required) = true];
  string location = 2;
  string project_id = 3;
  DataprocClusterResourceProfile resource_profile = 4 [(pipeline_models.validation.is_required) = true];
  // Optional field for Spark properties to run on a serverless cluster, See https://docs.cloud.google.com/dataproc-serverless/docs/concepts/properties for details.
  map<string, string> properties = 5;
  repeated string impersonation_chain = 6;
}

message DataprocClusterResourceProfile {
  message InlineConfig {
      oneof config_alias {
        // A Dataproc cluster config.
        // See: https://docs.cloud.google.com/dataproc/docs/reference/rest/v1/ClusterConfig
        google.protobuf.Struct cluster_config = 1 [deprecated = true];

        // A Dataproc cluster config.
        // See: https://docs.cloud.google.com/dataproc/docs/reference/rest/v1/ClusterConfig
        // For instance group config (e.g. machineTypeUri), see: https://docs.cloud.google.com/dataproc/docs/reference/rest/v1/InstanceGroupConfig
        google.protobuf.Struct config = 2;
      }
  }
  oneof config {
      InlineConfig inline = 1;
      string path = 2;
      string external_config_path = 3;
  }
  // Overrides are applied with deep merge onto the inline or external config. The format of Dataproc cluster config is required.
  // See: https://docs.cloud.google.com/dataproc/docs/reference/rest/v1/ClusterConfig
  // For instance group config (e.g. machineTypeUri), see: https://docs.cloud.google.com/dataproc/docs/reference/rest/v1/InstanceGroupConfig
  InlineConfig overrides = 4;
}

message DataprocBatchResourceProfile {
  message InlineConfig {
    // A Dataproc runtime config for a batch job.
    // See: https://docs.cloud.google.com/dataproc-serverless/docs/reference/rest/v1/RuntimeConfig
    google.protobuf.Struct runtime_config = 1;
    // A Dataproc environment config for a batch job.
    // See: https://docs.cloud.google.com/dataproc-serverless/docs/reference/rest/v1/EnvironmentConfig
    google.protobuf.Struct environment_config = 2;
  }
  oneof config {
    InlineConfig inline = 1;
    string path = 2;
    string external_config_path = 3;
  }
  // Overrides are applied with deep merge onto the inline or external config. Only runtime_config and environment_config are supported.
  // See: https://docs.cloud.google.com/dataproc-serverless/docs/reference/rest/v1/projects.locations.sessions#resource:-session
  InlineConfig overrides = 4;
}

message DataprocServerlessBatchEngine {
  string location = 1;
  DataprocBatchResourceProfile resource_profile = 2 [(pipeline_models.validation.is_required) = true];
  repeated string impersonation_chain = 3;
}


/////////////////////////
// Actions
////////////////////////
message Action {
  // NOTE: YAML mapping for oneof:
  // actions:
  //   - pyspark: { ... }
  //   - pipeline: { ... }
  //   - data_ingestion: { ... }
  //   - orchestration_pipeline: { ... }
  //   - ai: { ... }
  // Do NOT use a "type" field.
  oneof action {
    PythonAction python = 1;
    PysparkAction pyspark = 2;
    NotebookAction notebook = 3;
    SqlAction sql = 4;
    PipelineAction pipeline = 5;
    DataIngestionAction data_ingestion = 6;
    OrchestrationPipelineAction orchestration_pipeline = 7;
    AIAction ai = 8;
  }
}

/////////////////////////
// Python Action
////////////////////////
message PythonAction {
  string name = 1 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_.-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  repeated string depends_on = 2;
  string execution_timeout = 3 [(pipeline_models.validation.is_iso8601_duration) = true];
  string main_file_path = 4 [(pipeline_models.validation.is_required) = true];
  string python_callable = 5 [(pipeline_models.validation.is_required) = true];
  google.protobuf.Struct op_kwargs = 6;
  // Optional. If omitted or requirements are not specified, executes as standard
  // PythonOperator in the Airflow worker host environment.
  // When requirements are specified, executes as PythonVirtualenvOperator in an isolated virtualenv.
  PythonEnvironment environment = 7;
  PythonEngine engine = 8 [(pipeline_models.validation.is_required) = true];
  TriggerRule trigger_rule = 9; // Default: all_success.
}

message PythonEnvironment {
  message InlineRequirements {
    // list of pip packages
    repeated string list = 1;
  }
  message Requirements {
    oneof requirements {
      InlineRequirements inline = 1;
      string path = 2; // e.g. path: "requirements.txt"
    }
  }

  // Optional pip requirements. If omitted, task runs as standard PythonOperator.
  Requirements requirements = 1;
  bool system_site_packages = 2; // Default: false.
}

message PythonEngine {
  oneof engine {
    LocalEngine local = 1;
  }
}


/////////////////////////
// PySpark Action
////////////////////////
message PysparkAction {
  string name = 1 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_.-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  repeated string depends_on = 2;
  string execution_timeout = 3 [(pipeline_models.validation.is_iso8601_duration) = true];
  PysparkEngine engine = 4 [(pipeline_models.validation.is_required) = true];
  string main_file_path = 5 [(pipeline_models.validation.is_required) = true];
  repeated string archive_uris = 6;
  string staging_bucket = 7;
  repeated string py_files = 8;
  PysparkEnvironment environment = 9;
  TriggerRule trigger_rule = 10; // Default: all_success.
  // Parameters passed to the PySpark job.
  map<string, string> params = 11 [
    (pipeline_models.validation.map_key_regex) = "^[a-zA-Z0-9_-]+$",
    (pipeline_models.validation.map_value_regex) = "^[^';|`&]+$"
  ];
  map<string, string> labels = 12;
}

message PysparkEngine {
  oneof engine {
    DataprocOnGceEngine dataproc_on_gce = 1;
    DataprocServerlessBatchEngine dataproc_serverless = 2;
  }
}

message PysparkEnvironment {
  message InlineRequirements {
    // list of pip packages
    repeated string list = 1;
  }
  message Requirements {
    oneof requirements {
      string path = 1; // e.g. path: "requirements.txt"
      InlineRequirements inline = 2;
    }
  }
  Requirements requirements = 1;
}

/////////////////////////
// Notebook Action
////////////////////////
message NotebookAction {
  string name = 1 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_.-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  repeated string depends_on = 2;
  string execution_timeout = 3 [(pipeline_models.validation.is_iso8601_duration) = true];
  NotebookEngine engine = 4 [(pipeline_models.validation.is_required) = true];
  string main_file_path = 5 [(pipeline_models.validation.is_required) = true];
  repeated string archive_uris = 6;
  string staging_bucket = 7;
  NotebookEnvironment environment = 8;
  TriggerRule trigger_rule = 9; // Default: all_success.
  map<string, string> params = 10 [
    (pipeline_models.validation.map_key_regex) = "^[a-zA-Z0-9_-]+$",
    (pipeline_models.validation.map_value_regex) = "^[^';|`&]+$"
  ];
  map<string, string> labels = 11;
}

message NotebookEngine {
  oneof engine {
    DataprocOnGceEngine dataproc_on_gce = 1;
    DataprocServerlessBatchEngine dataproc_serverless = 2;
  }
}

message NotebookEnvironment {
  message InlineRequirements {
    // list of pip packages
    repeated string list = 1;
  }
  message Requirements {
    oneof requirements {
      string path = 1; // e.g. path: "requirements.txt"
      InlineRequirements inline = 2;
    }
  }
  Requirements requirements = 1;
}


/////////////////////////
// SQL Action
////////////////////////
message SqlAction {
  string name = 1 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_.-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  repeated string depends_on = 2;
  string execution_timeout = 3 [(pipeline_models.validation.is_iso8601_duration) = true];
  SqlEngine engine = 4 [(pipeline_models.validation.is_required) = true];
  Query query = 5 [(pipeline_models.validation.is_required) = true];
  TriggerRule trigger_rule = 6; // Default: all_success.
  // Runtime parameters for sql action.
  map<string, string> params = 7 [
    (pipeline_models.validation.map_key_regex) = "^[a-zA-Z0-9_-]+$",
    (pipeline_models.validation.map_value_regex) = "^[^';|`&]+$"
  ];
  map<string, string> labels = 8;
}

message Query {
  oneof query {
    string inline = 1;
    string path = 2;
   }
}

message SqlEngine {
  oneof engine {
    BigQueryEngine bigquery = 1;
    DataprocServerlessBatchEngine dataproc_serverless = 2;
    DataprocOnGceEngine dataproc_on_gce = 3;
  }
}


/////////////////////////
// Pipeline
////////////////////////
message PipelineAction {
  string name = 1 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_.-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  repeated string depends_on = 2;
  string execution_timeout = 3 [(pipeline_models.validation.is_iso8601_duration) = true];
  PipelineFramework framework = 4 [(pipeline_models.validation.is_required) = true];
  TriggerRule trigger_rule = 5; // Default: all_success.

  // Note: 'params' is currently not supported when executing Dataform using Dataform Service.
  map<string, string> params = 6 [
    (pipeline_models.validation.map_key_regex) = "^[a-zA-Z0-9_-]+$",
    (pipeline_models.validation.map_value_regex) = "^[^';|`&]+$"
  ];
  // Note: 'labels' is currently not supported when executing DBT or Dataform using Dataform Service.
  map<string, string> labels = 7;
}

message PipelineFramework {
  oneof framework {
    DbtFrameworkSpec dbt = 1;
    DataformFrameworkSpec dataform = 2;
  }
}

message DbtFrameworkSpec {
  oneof execution {
    // Execute DBT using Airflow Worker (local execution).
    DbtAirflowExecution airflow_worker = 1;
  }
}

message DataformFrameworkSpec {
  oneof execution {
    // Execute Dataform using Dataform Service.
    DataformServiceExecution dataform_service = 1;
    // Execute Dataform using Airflow Worker (local execution).
    DataformAirflowExecution airflow_worker = 2;
  }
}

// Configuration for executing on Dataform Service.
message DataformServiceExecution {
  string location = 1;
  string project_id = 2;
  string repository_id = 3 [(pipeline_models.validation.is_required) = true];
  // Configuration for the workflow invocation, which specifies which actions to run.
  // See: https://docs.cloud.google.com/php/docs/reference/cloud-dataform/latest/V1beta1.WorkflowInvocation
  google.protobuf.Struct workflow_invocation = 4;
}

// Configuration for executing DBT on Airflow Worker.
message DbtAirflowExecution {
  // Relative path to folder containing DBT project.
  string project_directory_path = 1 [(pipeline_models.validation.is_required) = true];
  // List of models to include in the run (equivalent to dbt --select).
  repeated string select_models = 2;
  repeated string tags = 3;
}

// Configuration for executing Dataform on Airflow Worker.
message DataformAirflowExecution {
  string project_directory_path = 1 [(pipeline_models.validation.is_required) = true];
}

/////////////////////////
// Data Ingestion Action
////////////////////////
message DataIngestionAction {
  string name = 1 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_.-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  repeated string depends_on = 2;
  string execution_timeout = 3 [(pipeline_models.validation.is_iso8601_duration) = true];

  oneof config {
    BigQueryDtsSpec bigquery_dts = 4;
  }
  TriggerRule trigger_rule = 5; // Default: all_success.
}

message BigQueryDtsSpec {
  oneof transfer_config {
    string transfer_config_id = 1 [(pipeline_models.validation.is_required) = true];
  }
  google.protobuf.Struct runtime_params = 2 [deprecated = true];

  message TimeRange {
    string start_time = 1 [(pipeline_models.validation.is_iso8601_timestamp) = true];
    string end_time = 2 [(pipeline_models.validation.is_iso8601_timestamp) = true];
  }
  oneof time {
    // See: https://docs.cloud.google.com/bigquery/docs/reference/datatransfer/rpc/google.cloud.bigquery.datatransfer.v1#timerange
    TimeRange requested_time_range = 6;
    string requested_run_time = 7 [(pipeline_models.validation.is_iso8601_timestamp) = true];
  }

  repeated string impersonation_chain = 3;
  string project_id = 4;
  string location = 5;
}

/////////////////////////////////////
// Orchestration Pipeline Action
////////////////////////////////////
message OrchestrationPipelineAction {
  string name = 1 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_.-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  repeated string depends_on = 2;
  string execution_timeout = 3 [(pipeline_models.validation.is_iso8601_duration) = true];

  string pipeline_id = 4 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  string bundle_id = 5;
  bool wait_for_completion = 6; // Default: false.
  TriggerRule trigger_rule = 7; // Default: all_success.
}

/////////////////////////////////////
// AI Action
////////////////////////////////////
message AIAction {
  string name = 1 [
    (pipeline_models.validation.is_required) = true,
    (pipeline_models.validation.regex) = "^[a-zA-Z0-9_.-]+$",
    (pipeline_models.validation.min_len) = 1,
    (pipeline_models.validation.max_len) = 64
  ];
  repeated string depends_on = 2;
  string execution_timeout = 3 [(pipeline_models.validation.is_iso8601_duration) = true];
  TriggerRule trigger_rule = 4; // Default: all_success.

  oneof provider {
    AgentPlatform agent_platform = 5;
  }

  map<string, string> labels = 6;
}

message AgentPlatform {
  string project_id = 1;
  string location = 2;

  oneof type {
    AgentPlatformModelUpload model_upload = 3;
    AgentPlatformBatchInference batch_inference = 4;
  }
}

message AgentPlatformModelUpload {
  string model_name = 1 [(pipeline_models.validation.is_required) = true];
  string description = 2;
  string model_artifact_uri = 3 [(pipeline_models.validation.is_required) = true];
  string serving_container_image_uri = 4 [(pipeline_models.validation.is_required) = true];
}

message AgentPlatformBatchInference {
  string job_display_name = 1 [(pipeline_models.validation.is_required) = true];
  string model_name = 2 [(pipeline_models.validation.is_required) = true];
  string instances_format = 3;
  string predictions_format = 4;
  string bigquery_source = 5;
  repeated string gcs_source = 6;
  string bigquery_destination_prefix = 7;
  string gcs_destination_prefix = 8;
  repeated string impersonation_chain = 12;
}

## Orchestration Pipeline YAML File example
```yaml
modelVersion: 1.0
pipelineId: sample_orchestration
description: Orchestrate dbt after pyspark
runner: airflow
owner: data-eng-team
tags:
  - "job:datacloud:antigravity"

defaults:
  projectId: your-project-id
  location: us-central1
  executionConfig:
    retries: 1

triggers:
  - schedule:
      interval: "0 0 * * *"
      startTime: "2025-10-01T00:00:00"
      endTime: "2026-10-01T00:00:00"
      catchup: false
      timezone: UTC

actions:
  - pyspark:
      name: my_pyspark_job
      engine:
        dataprocOnGce:
          existingCluster:
            clusterName: my-cluster
            location: us-central1
            projectId: your-project-id
      mainFilePath: path/to/script.py

  - pipeline:
      name: my_dbt_pipeline
      dependsOn:
        - my_pyspark_job
      framework:
        dbt:
          airflowWorker:
            projectDirectoryPath: path/to/dbt_project
  - ai:
      name: "upload_model_vertex"
      agentPlatform:
        modelUpload:
          modelName: "model_name"
          description: "Model description"
          modelArtifactUri: path/to/model/artifact
          servingContainerImageUri: path/to/serving/image

```

## Key Schema Reminders:
1. **Action Key**: Use `- pyspark:`, `- notebook:`, `- sql:`, `- pipeline:`, `- data_ingestion:`, `- orchestration_pipeline:`, or `- ai:` directly as the key. Do NOT use `- type: pyspark`.
2. **Dataproc Engine**: Under `dataprocOnGce`, you **MUST** specify either `existingCluster` (with `clusterName`) or `ephemeralCluster` (with `clusterName` and `resourceProfile`). For Serverless Dataproc, use `dataprocServerless: {}`.
3. **Environment Requirements**:
   - The `environment` field is **optional** on `python` actions. Omit `environment` to run using standard `PythonOperator` when extra dependencies are not required.
   - When custom dependencies are needed, specifying `requirements` compiles to `PythonVirtualenvOperator`:
     - For file dependencies: `environment.requirements.path: "requirements.txt"`
     - For inline dependencies: **MUST** use nested `list` under `inline` (`environment.requirements.inline.list: ["pkg1", "pkg2"]`). Do NOT pass an array directly to `inline`.
4. **Action Params (`params`)**:
   - Keys must match regex `^[a-zA-Z0-9_-]+$` (only alphanumeric, underscores, and hyphens).
   - Values must match regex `^[^';|`&]+$` (cannot contain `'`, `;`, `|`, `` ` ``, `&`).
5. **SQL Action Location & Query Guidelines**:
   - **BigQuery (`engine.bigquery`)**: Always set `location` to match the dataset's region/multi-region. Specify the target table via `destinationTable` and use pure `SELECT` queries without DDL statements (do NOT use `CREATE TABLE` or `CREATE OR REPLACE TABLE`).
   - **Dataproc (`engine.dataprocServerless` / `engine.dataprocOnGce`)**: Dataproc engines do not have a `destinationTable` field; include DDL/DML statements (`CREATE TABLE ... AS SELECT ...` or `INSERT OVERWRITE ...`) directly within the SQL query text to persist tables.