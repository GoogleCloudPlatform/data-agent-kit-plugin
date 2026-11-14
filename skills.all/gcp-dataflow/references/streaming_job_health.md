# Streaming Job Health Analysis

## 1. Job Health Classification

Dataflow streaming job health is primarily determined by the behavior and
latency of its **data watermark**.

*   **Health Status: Healthy**

    *   **Criteria**: Data watermark is stable and close to real-time ($\le$ 1
        minute delay).

*   **Health Status: Mostly Healthy**

    *   **Criteria**:
        *   Watermark is stable but sits at a slightly higher constant baseline
            delay. ($\le$ 5 minute delay).
        *   Job started with a massive backlog, but the backlog is steadily
            decreasing. > [!NOTE] > Watermark progress during backlog clearance
            is frequently spiky/un-smooth due to out-of-order processing bounds
            (common with Pub/Sub sources).

*   **Health Status: Not Healthy**

    *   **Criteria**: Watermark is significantly delayed (several minutes)
        and/or exhibits recurring or growing latency spikes.

## 2. Telemetry & Analysis Guidelines

### Runtime Sufficiency

*   **Requirement**: A job needs a minimum of **5 minutes of active telemetry**
    to accumulate enough telemetry/trends for a reliable health determination.

### Diagnostic Strategy for Unhealthy Jobs

When a pipeline is flagged as **Not Healthy**, investigate by correlating metric
fluctuations with other metrics and worker logs:

1.  **Bottlenecks**: Analyze queue delays utilizing `job/is_bottleneck`.
2.  **Parallelism constraints**: Check for insufficient key cardinality or hot
    keys (`job/backlogged_keys`).
3.  **Stuck execution**: Audit worker logs for thread stack dumps, slow HTTP/DB
    client calls, or long-running operations.

### Temporal Analysis (Timeline Segmentation)

If a pipeline's behavior changes over the observed window (e.g., healthy
$\rightarrow$ unhealthy, or shifts in bottleneck causes):

*   Do not aggregate the entire spans of contrasting behaviors as a single
    state.
*   **Segment the timeline** into distinct phases of behavior and analyze
    telemetry/root causes independently for each.
*   *Oscillation Caveat*: If stage bottlenecks repeatedly oscillate between the
    same causes, summarize it as a single recurring phase of behavior.

### Corroboration & Uncertainty Handling

*   **Multi-Metric Validation**: Proactively prevent false positives.
    Corroborate all hypothesized root causes across multiple telemetry sources
    (e.g., validate a bottleneck `likely_cause` against watermark age spikes,
    resource saturation, and worker log exceptions).
*   **Speculation Avoidance**: Explicitly state uncertainty when data is
    ambiguous or incomplete. Avoid highly speculative conclusions, as directing
    the user down the wrong troubleshooting path leads to high developer toil.
