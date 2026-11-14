## Streaming Engine Metrics

*Useful for debugging Dataflow Streaming Engine Jobs.*

<!-- disableFinding(LIST_NO_LINE) -->

### `job/backlogged_keys`

*   **Display Name**: Backlogged Keys
*   **Summary**: The number of backlogged keys for a bottleneck stage.
*   **Kind/Type**: GAUGE, INT64, 1
*   **Filter Labels**: `job_id`, `stage`

### `job/bundle_user_processing_latencies`

*   **Display Name**: Bundle user processing latencies
*   **Summary**: Bundle user processing latencies from a particular stage.
    Available for jobs running on Streaming.
*   **Kind/Type**: GAUGE, DISTRIBUTION, ms
*   **Filter Labels**: `job_id`, `stage`

### `job/processing_parallelism_keys`

*   **Display Name**: The approximate number of parallel processing keys
*   **Summary**: Approximate number of keys in use for data processing for each
    stage.
*   **Kind/Type**: GAUGE, INT64, 1
*   **Filter Labels**: `job_id`, `stage`

### `job/recommended_parallelism`

*   **Display Name**: Recommended Parallelism
*   **Summary**: The recommended parallelism for a stage to reduce
    bottlenecking.
*   **Kind/Type**: GAUGE, INT64, 1
*   **Filter Labels**: `job_id`, `stage`

### `job/streaming_engine/key_processing_availability`

*   **Display Name**: Current processing key-range availability
*   **Summary**: Percentage of streaming processing keys that are assigned to
    workers and available to perform work.
*   **Kind/Type**: GAUGE, DOUBLE, 10^2.%
*   **Filter Labels**: `job_id`, `stage`

### `job/streaming_engine/persistent_state/read_bytes_count`

*   **Display Name**: Storage bytes read
*   **Summary**: Storage bytes read by a particular stage. Available for jobs
    running on Streaming Engine. Sampled every 60 seconds.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `job_id`, `stage`

### `job/streaming_engine/persistent_state/stored_bytes`

*   **Display Name**: Current persistence state usage
*   **Summary**: Current bytes stored in persistent state for the job.
*   **Kind/Type**: GAUGE, INT64, By
*   **Filter Labels**: `job_id`

### `job/streaming_engine/persistent_state/write_bytes_count`

*   **Display Name**: Storage bytes written
*   **Summary**: Storage bytes written by a particular stage. Available for jobs
    running on Streaming Engine. Sampled every 60 seconds.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `job_id`, `stage`

### `job/streaming_engine/persistent_state/write_latencies`

*   **Display Name**: Storage write latencies
*   **Summary**: Storage write latencies from a particular stage. Available for
    jobs running on Streaming Engine.
*   **Kind/Type**: DELTA, DISTRIBUTION, ms
*   **Filter Labels**: `job_id`, `stage`

### `job/streaming_engine/stage_end_to_end_latencies`

*   **Display Name**: Per stage end to end latencies.
*   **Summary**: Distribution of time spent by streaming engine in each stage of
    the pipeline.
*   **Kind/Type**: GAUGE, DISTRIBUTION, ms
*   **Filter Labels**: `job_id`, `stage`

### `job/timers_pending_count`

*   **Display Name**: Timers pending count per stage
*   **Summary**: The number of timers pending in a particular stage. Available
    for jobs running on Streaming Engine.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `job_id`, `stage`

### `job/timers_processed_count`

*   **Display Name**: Timers processed count per stage
*   **Summary**: The number of timers completed by a particular stage. Available
    for jobs running on Streaming Engine.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `job_id`, `stage`

### `job/horizontal_worker_scaling`

*   **Display Name**: Horizontal worker scaling
*   **Summary**: A boolean indicating the recommended horizontal scaling
    direction and rationale. True means the scaling decision took effect, false
    otherwise.

*   **Kind/Type**: GAUGE, BOOL, 1

*   **Filter Labels**: `job_id`, `rationale`, `direction`

### `job/max_worker_instances_limit`

*   **Display Name**: Job max worker instances limit
*   **Summary**: The maximum number of workers autoscaling is allowed to
    request.
*   **Kind/Type**: GAUGE, INT64, 1
*   **Filter Labels**: `job_id`

### `job/min_worker_instances_limit`

*   **Display Name**: Job min worker instances limit
*   **Summary**: The minimum number of workers autoscaling is required to
    request.
*   **Kind/Type**: GAUGE, INT64, 1
*   **Filter Labels**: `job_id`

### `job/worker_utilization_hint`

*   **Display Name**: Job worker utilization hint
*   **Summary**: User worker utilization hint set by customers to define a
    target worker CPU utilization range for horizontal autoscaling, influencing
    scaling aggressiveness. A value of 0 indicates the hint is not actively
    used.
*   **Kind/Type**: GAUGE, DOUBLE, 10^2.%
*   **Filter Labels**: `job_id`

### `job/worker_utilization_hint_is_actively_used`

*   **Display Name**: Job worker utilization hint is actively used
*   **Summary**: Reports whether or not the worker utilization hint is actively
    used by the horizontal autoscaling policy.
*   **Kind/Type**: GAUGE, BOOL, 1
*   **Filter Labels**: `job_id`
