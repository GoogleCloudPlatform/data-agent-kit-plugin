# Bottlenecks and Parallelism Context

## 1. Scalability, Keys, and Parallelism

Dataflow Streaming Engine operates on a **per-key processing model** to scale to
tens of millions of messages per second while ensuring exactly-once processing.

### Relevant metrics

Specific metrics to reference in
[dataflow_metrics_streaming_engine](dataflow_metrics_streaming_engine.md)

*   `job/processing_parallelism_keys` for parallelism
*   `job/bundle_user_processing_latencies` for operation processing age,
    indicating slow or stuck processing operations
*   `job/streaming_engine/stage_end_to_end_latencies` for total end to end time
    including all queueing, shuffling, and user processing.

### Key-Based Orchestration

*   **Definition**: A key is an identifier linking related messages across time
    (e.g., in `GroupByKey` for aggregations). State is persisted per key.
*   **Explicit vs. Implicit Keys**:
    *   *Explicit*: User-defined keys resulting from pipeline design (e.g.,
        grouped-by keys).
    *   *Implicit*: Assigned automatically by the system when no semantic key
        exists (e.g., reading from Pub/Sub) to track system metadata and
        exactly-once state.
*   **Serial Processing**: Message processing is strictly **serialized per key**
    within a fused stage.
    *   *Mechanism*: While a batch of messages is processing for active key $K$,
        subsequent messages for $K$ are buffered.
    *   *Rationale*: Permits highly efficient state caching and "blind writes",
        avoiding expensive transactions or fine-grained synchronization
        barriers.
    *   *Minimum State*: Under the hood, even purely stateless fused stages
        mutate exactly-once tracking state.

### Parallelism Constraints

*   **Upper Bound**: The number of unique active keys represents the strict
    upper limit of parallel execution threads.
*   **Bottlenecks & Amdahl's Law**:
    *   *Low Key Cardinality*: Insufficient key variety constrains parallel
        execution, leading to idle workers and slow processing.
    *   *Hot Keys*: Uneven distribution of traffic where a tiny subset of keys
        receives the majority of records. This serializes processing on those
        specific keys, creating a major processing bottleneck (high watermark
        age, backlog).
    *   *High Key Cardinality*: Extremely high cardinality of keys together with
        elevated processing delay can cause excessive queueing delay.

## 2. Long-Running or Stuck Operations

Most User-Defined Functions (UDFs/`DoFn`s) execute in milliseconds. External
service RPCs or synchronous, blocking calls can stall execution.

### The Blockage Cascade

*   **Key-Level Head-of-Line Blocking**: Because processing is serial per key, a
    stuck or long-running operation on key $K$ blocks **all downstream and
    future messages** assigned to $K$.
*   **Exactly-Once Constraint**: Waiting data is never dropped to guarantee
    exactly-once safety.
*   **System-Wide Backpressure**: As blocked queues for specific keys grow and
    exceed flow control/memory thresholds, the pipeline applies backpressure
    upstream. This ultimately suspends all processing, including healthy keys.

### Remediation & Best Practices

*   **Optimized Connectors**: Prefer managed, highly-scaled built-in I/O sinks
    (`PubsubIO`, `BigQueryIO`) over custom HTTP/RPC implementations.
*   **Resilient Custom I/O**: If custom external calls are necessary, to ensure
    performance always use:
    *   Strict client/network timeouts.
    *   Bounded retries with exponential backoff.
    *   Batching to group multiple elements into single RPC calls.
    *   During bundle processing parallelize external rpcs instead of issuing
        and joining sequentially.

## 3. Queue Bottlenecks & Backlog Propagation

Streaming pipelines connect components (Streaming Shuffle, `DoFn` threads, and
State Checkpoints) via sequential **queues** flowing from upstream to
downstream.

### Root Cause vs. Symptom

*   **Backpressure Propagation**: A bottleneck in a downstream component causes
    queues to grow upstream. Once the downstream buffer queue reaches capacity:
    1.  Downstream applies backpressure.
    2.  Upstream shuffle/read operations pause.
    3.  High latency/backlog propagates all the way upstream to the source.
*   **Debug Challenge**: Backpressure makes the entire pipeline appear degraded,
    obscuring the true bottleneck. Target the precise component blocking the
    queue.

### Detection & Thresholds

*   **Trigger**: Streaming dataflow bottleneck detection flags a stage as a
    bottleneck when system queue delay exceeds **5 minutes**.
*   **Assessment**:
    *   Transient delays exceeding 5 minutes (e.g., from traffic spikes) may
        resolve naturally and might not require intervention.
    *   Check the `job/is_bottleneck` metric (and fields `likely_cause`,
        `bottleneck_kind`) to pinpoint root causes and remediate per the
        [Dataflow Bottlenecks Troubleshooting Guide](https://docs.cloud.google.com/dataflow/docs/guides/troubleshoot-bottlenecks).
