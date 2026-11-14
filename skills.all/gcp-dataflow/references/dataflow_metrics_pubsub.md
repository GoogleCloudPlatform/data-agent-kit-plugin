## Pub/Sub Metrics

*Useful for debugging Dataflow Jobs with Pubsub source/sink.*

<!-- disableFinding(LIST_NO_LINE) -->
### `job/pubsub/late_messages_count`
*   **Display Name**: Pub/Sub Late Messages Count
*   **Summary**: The number of messages from Pub/Sub with timestamp older than
    the estimated watermark. Sampled every 60 seconds.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `job_id`, `stage`, `subscription_project_id`,
    `subscription_id`, `topic_project_id`, `topic_id`

### `job/pubsub/published_messages_count`
*   **Display Name**: Pub/Sub Published Messages Count
*   **Summary**: The number of Pub/Sub messages published broken down by topic
    and status. Sampled every 60 seconds.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `job_id`, `stage`, `topic_project_id`, `topic_id`,
    `status`

### `job/pubsub/pulled_message_ages`
*   **Display Name**: Pub/Sub Pulled Message Ages
*   **Summary**: The distribution of pulled but unacked Pub/Sub message ages.
    Sampled every 60 seconds.
*   **Kind/Type**: GAUGE, DISTRIBUTION, ms
*   **Filter Labels**: `job_id`, `stage`, `subscription_project_id`,
    `subscription_id`, `topic_project_id`, `topic_id`

### `job/pubsub/read_count`
*   **Display Name**: PubsubIO.Read requests from Dataflow jobs
*   **Summary**: Pub/Sub Pull Requests. For Streaming Engine, this metric is
    deprecated.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `status`, `job_id`, `ptransform`,
    `subscription_project_id`, `subscription_id`, `topic_project_id`, `topic_id`

### `job/pubsub/read_latencies`
*   **Display Name**: Pub/Sub Pull Request Latencies
*   **Summary**: Pub/Sub Pull request latencies from PubsubIO.Read in Dataflow
    jobs. For Streaming Engine, this metric is deprecated.
*   **Kind/Type**: DELTA, DISTRIBUTION, ms
*   **Filter Labels**: `job_id`, `ptransform`, `subscription_project_id`,
    `subscription_id`, `topic_project_id`, `topic_id`

### `job/pubsub/streaming_pull_connection_status`
*   **Display Name**: Percentage of active/terminated Streaming Pull connections
*   **Summary**: Percentage of all Streaming Pull connections that are either
    active (OK status) or terminated because of some error.
*   **Kind/Type**: GAUGE, DOUBLE, %
*   **Filter Labels**: `status`, `job_id`, `ptransform`,
    `subscription_project_id`, `subscription_id`, `topic_project_id`, `topic_id`

### `job/pubsub/timestamp_events`
*   **Display Name**: Pub/Sub Event Timestamp Status
*   **Summary**: The number of Pub/Sub messages with event timestamps broken
    down by topic and status. Sampled every 60 seconds.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `job_id`, `stage`, `topic_project_id`, `topic_id`,
    `status`

### `job/pubsub/write_count`
*   **Display Name**: Pub/Sub Publish Requests
*   **Summary**: Pub/Sub Publish requests from PubsubIO.Write in Dataflow jobs.
    Sampled every 60 seconds.
*   **Kind/Type**: DELTA, INT64, 1
*   **Filter Labels**: `status`, `job_id`, `ptransform`, `topic_project_id`,
    `topic_id`

### `job/pubsub/write_latencies`
*   **Display Name**: Pub/Sub Publish Request Latencies
*   **Summary**: Pub/Sub Publish request latencies from PubsubIO.Write in
    Dataflow jobs. Sampled every 60 seconds.
*   **Kind/Type**: DELTA, DISTRIBUTION, ms
*   **Filter Labels**: `job_id`, `ptransform`, `topic_project_id`, `topic_id`
