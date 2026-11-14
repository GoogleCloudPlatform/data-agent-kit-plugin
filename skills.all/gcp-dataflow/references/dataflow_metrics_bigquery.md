## BigQuery Metrics

*Useful for Evaluating BigQuery sink write failures or delays.*

### `job/bigquery/write_count`

*   **Display Name**: BigQueryIO.Write Requests
*   **Summary**: BigQuery write requests from BigQueryIO.Write in Dataflow jobs.
    Sampled every 60 seconds.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `status`, `job_id`, `ptransform`, `bigquery_project_id`,
    `bigquery_dataset_id`, `bigquery_table_or_view_id`
