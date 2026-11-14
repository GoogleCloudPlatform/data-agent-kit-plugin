# Dataflow Streaming Horizontal Autoscaling Analysis

Use this reference to analyze Dataflow horizontal autoscaling behavior and
diagnose limits or anomalies. For complete telemetry, correlate this analysis
with the metrics defined in
[Streaming Engine Metrics](dataflow_metrics_streaming_engine.md).

## 1. Autoscaling Health Standards

*   **Worker CPU Utilization**:
    *   **Healthy Behavior**: Stabilizes around default **70%** under load.
    *   **Anomalous / Unhealthy Behavior**: Extremely underutilized
        ($<20\%$) or completely saturated ($>90\%$) while the pipeline is
        unhealthy.
*   **Estimated Backlog**:
    *   **Healthy Behavior**: Kept low (consistently near zero).
    *   **Anomalous / Unhealthy Behavior**: Steadily growing backlog time.
*   **Worker Count**:
    *   **Healthy Behavior**: Fluidly scales up/down with traffic.
    *   **Anomalous / Unhealthy Behavior**: Restricted by
        `job/max_worker_instances_limit` or `job/min_worker_instances_limit`
        bounds.
*   **Autoscaling Decisions**: Query the `job/horizontal_worker_scaling` metric
    and inspect the `rationale` field to identify the specific logic triggers
    behind scaling choices. These triggers can be further correlated with
    pipeline diagnostics.

## 2. How the Autoscaler Operates

This is an overview, there are heuristics and edge cases that prevent the
operation here described, but in most cases, the following rules apply.

*   **Standard Scale Up**: Triggered when estimated backlog processing time
    exceeds scale up triggering threshold.
*   **Proactive Scale Up (High CPU)**: If CPU utilization spikes aggressively,
    the autoscaler proactively upscales *before* a backlog develops, absorbing
    resource-intensive traffic bursts.
*   **Standard Scale Down**: Triggered only when **both** estimated backlog and
    CPU utilization are low.

## 3. Critical Gotchas & Anomalous States

### Undetected Throttling (Crucial Debug Scenario)

*   **Mechanism**: If a pipeline is capped by IO latency, locks, poor
    utilization, or downstream write limits (throttled), the autoscaler's
    heuristic engine might fail to detect the restriction.
*   **Symptom Cascade**:
    1.  Estimated backlog continues to rise.
    2.  Overall worker CPU utilization remains low (workers are idle waiting for
        downstream RPCs).
    3.  The autoscaler endlessly adds workers, scaling all the way to the
        maximum worker limit.
*   **Root Causes**:
    *   **IO Bottlenecks**: Third-party API quotas, external resource
        provisioning, or custom IO blockages.
    *   **Insufficient Parallelism / Hot Keys**: Under-partitioned key spaces
        serialize work on a few keys. This leaves most workers idle (low CPU)
        while backlogs accumulate, causing identical false upscaling.

## 4. Mitigation & In-Flight Controls

For troubleshooting or optimizing scaling behavior, recommend updating the
running job with the following parameters (see
[Dataflow In-Flight Updates](https://docs.cloud.google.com/dataflow/docs/guides/updating-a-pipeline#in-flight-updates)):

*   **Worker Utilization Hint (`job/worker_utilization_hint`)**:
    *   Customizes the target CPU utilization for downscaling.
    *   *Lower hint*: Prevents aggressive worker termination, retaining warm
        capacity.
    *   *Higher hint*: Maximizes worker density but requires highly parallelized
        workloads to prevent backlog spikes.
*   **Clamping Bounds (`job/max_worker_instances_limit` /
    `job/min_worker_instances_limit`)**:
    *   Forces strict bounds on the pool, overriding autoscaler decisions to
        prevent cost runaways or stabilize performance during spikes.

## 5. Algorithmic Scale-Up Bias & Support Escalation

*   **Latency-Minimization Bias**: When encountering telemetry uncertainty, the
    core autoscaling engine purposefully biases towards upscaling to guarantee
    low data lag/watermark age. This trait values data freshness over
    infrastructure cost, occasionally generating cost spikes.
*   **Workload Diversity**: Heuristic autoscaling rules cannot model every
    pipeline structure perfectly. Telemetry patterns that succeed on one
    workload may fail on another.
*   **Support Escalation**: If no detectable source of throttling exists as
    outlined in the "Undetected Throttling" section, and applying in-flight
    mitigations (clamping limits, adjusting CPU hints) fails to yield desired
    autoscaling results, **recommend that the customer contact GCP Support**.
    Support engineers can provision deep backend tunings and custom engine
    configurations tailored to specific pipeline footprints.
