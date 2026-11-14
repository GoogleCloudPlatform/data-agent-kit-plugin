# Core Job Metrics

*Useful for analysing overall pipeline health, watermarks, and message rates.*

<!-- disableFinding(LIST_NO_LINE) -->
## `job/backlog_bytes`
*   **Display Name**: Per-stage backlog in bytes
*   **Summary**: Amount of known, unprocessed input for a stage, in bytes.
*   **Kind/Type**: GAUGE, INT64, By
*   **Filter Labels**: `job_id`, `stage`

### `job/backlog_elements`
*   **Display Name**: Per-stage backlog in elements
*   **Summary**: Amount of known, unprocessed input for a stage, in elements.
*   **Kind/Type**: GAUGE, INT64, 1
*   **Filter Labels**: `job_id`, `stage`

### `job/bundle_user_processing_latencies`
*   **Display Name**: Bundle user processing latencies
*   **Summary**: Bundle user processing latencies from a particular stage.
    Available for jobs running on Streaming.
*   **Kind/Type**: GAUGE, DISTRIBUTION, ms
*   **Filter Labels**: `job_id`, `stage`

### `job/data_watermark_age`
*   **Display Name**: Data watermark lag
*   **Summary**: The age (time since event timestamp) up to which all data has
    been processed by the pipeline.
*   **Kind/Type**: GAUGE, INT64, s
*   **Filter Labels**: `job_id`

### `job/dofn_latency_average`
*   **Display Name**: Average message processing time per DoFn.
*   **Summary**: The average processing time for a single message in a given
    DoFn (over the past 3 min window).
*   **Kind/Type**: GAUGE, DOUBLE, ms
*   **Filter Labels**: `job_id`, `do_fn`

### `job/estimated_timer_backlog_processing_time`
*   **Display Name**: Estimated time (in seconds) for timers to complete.
*   **Summary**: Estimated time (in seconds) for timers to complete. Only
    available for Streaming Engine jobs.
*   **Kind/Type**: GAUGE, INT64, s
*   **Filter Labels**: `job_id`, `stage`

### `job/is_bottleneck`
*   **Display Name**: Bottleneck Status and Likely Causes
*   **Summary**: Whether a specific Dataflow pipeline stage is a bottleneck,
    along with its bottleneck kind and likely cause.
*   **Kind/Type**: GAUGE, BOOL,
*   **Filter Labels**: `job_id`, `stage`, `likely_cause`, `bottleneck_kind`

### `job/longest_processing_time`
*   **Display Name**: Longest Processing Times
*   **Summary**: Top 10 oldest active operation times grouped by user worker.
    Sampled every 60 seconds.
*   **Kind/Type**: GAUGE, INT64, us
*   **Filter Labels**: `job_id`, `user_worker_id`

### `job/oldest_active_message_age`
*   **Display Name**: Oldest active message processing time per DoFn.
*   **Summary**: How long the oldest active message in a DoFn has been
    processing for.
*   **Kind/Type**: GAUGE, INT64, ms
*   **Filter Labels**: `job_id`, `do_fn`

### `job/per_stage_data_watermark_age`
*   **Display Name**: Per-stage data watermark lag
*   **Summary**: The age (time since event timestamp) up to which all data has
    been processed by this stage of the pipeline.
*   **Kind/Type**: GAUGE, INT64, s
*   **Filter Labels**: `job_id`, `stage`

### `job/per_stage_system_lag`

*   **Display Name**: Per-stage system lag
*   **Summary**: The current maximum duration that an item of data has been
    processing or awaiting processing in this stage.
*   **Kind/Type**: GAUGE, INT64, s
*   **Filter Labels**: `job_id`, `stage`

### `job/system_lag`

*   **Display Name**: System lag
*   **Summary**: The current maximum duration that an item of data has been
    processing or awaiting processing.
*   **Kind/Type**: GAUGE, INT64, s
*   **Filter Labels**: `job_id`

### `job/thread_time`

*   **Display Name**: Thread Time
*   **Summary**: Estimated time in milliseconds spent running in the function of
    the ptransform totaled across threads.
*   **Kind/Type**: DELTA, INT64, ms
*   **Filter Labels**: `job_id`, `ptransform`, `function`

### `job/user_counter`

*   **Display Name**: User Counter
*   **Summary**: A user-defined counter metric. Sampled every 60 seconds.
*   **Kind/Type**: GAUGE, DOUBLE, 1
*   **Filter Labels**: `metric_name`, `job_id`, `ptransform`

### `job/dofn_latency_max`
*   **Display Name**: Maximum message processing time per DoFn.
*   **Summary**: The maximum processing time for a single message in a given
    DoFn (over the past 3 min window).
*   **Kind/Type**: GAUGE, INT64, ms
*   **Filter Labels**: `job_id`, `do_fn`

### `job/dofn_latency_min`
*   **Display Name**: Minimum message processing time per DoFn.
*   **Summary**: The minimum processing time for a single message in a given
    DoFn (over the past 3 min window).
*   **Kind/Type**: GAUGE, INT64, ms
*   **Filter Labels**: `job_id`, `do_fn`

### `job/dofn_latency_num_messages`
*   **Display Name**: Number of messages processed per DoFn.
*   **Summary**: The number of messages processed by a given DoFn (over the past
    3 min window).
*   **Kind/Type**: GAUGE, INT64, 1
*   **Filter Labels**: `job_id`, `do_fn`

### `job/dofn_latency_total`
*   **Display Name**: Total message processing time per DoFn.
*   **Summary**: The total processing time for all messages in a given DoFn
    (over the past 3 min window).
*   **Kind/Type**: GAUGE, INT64, ms
*   **Filter Labels**: `job_id`, `do_fn`

### `job/element_count`
*   **Display Name**: Element count
*   **Summary**: Number of elements added to the pcollection so far. Sampled
    every 60 seconds. After sampling
*   **Kind/Type**: GAUGE, INT64, 1
*   **Filter Labels**: `job_id`, `pcollection`

### `job/elements_produced_count`
*   **Display Name**: Elements Produced
*   **Summary**: The number of elements produced by each PTransform. Sampled
    every 60 seconds.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `job_id`, `pcollection`, `ptransform`

### `job/estimated_backlog_processing_time`
*   **Display Name**: Estimated time to process current backlog per stage
*   **Summary**: Estimated time (in seconds) to consume current backlog if no
    new data comes in and throughput stays same.
*   **Kind/Type**: GAUGE, INT64, s
*   **Filter Labels**: `job_id`, `stage`

### `job/estimated_byte_count`
*   **Display Name**: Estimated byte count
*   **Summary**: An estimated number of bytes added to the pcollection so far.
*   **Kind/Type**: GAUGE, INT64, By
*   **Filter Labels**: `job_id`, `pcollection`

### `job/estimated_bytes_active`
*   **Display Name**: Active Size
*   **Summary**: Estimated number of bytes active in this stage of the job.
*   **Kind/Type**: GAUGE, INT64, By
*   **Filter Labels**: `job_id`, `stage`

### `job/estimated_bytes_consumed_count`
*   **Display Name**: Throughput
*   **Summary**: Estimated number of bytes consumed by the stage of this job.
*   **Kind/Type**: DELTA, INT64, By
*   **Filter Labels**: `job_id`, `stage`

### `job/estimated_bytes_produced_count`
*   **Display Name**: Estimated Bytes Produced
*   **Summary**: The estimated total byte size of elements produced by each
    PTransform. Sampled every 60 seconds.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `job_id`, `pcollection`, `ptransform`
