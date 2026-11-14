# Reporting Dataflow Investigation Findings & Diagnostics

The reader is an engineer or stakeholder who will act on this report: adjust
pipeline configurations, scale resources, restart a failing job, escalate, or
respond to users. They must be able to check any single claim in under a minute,
using the citation you provide, without re-running your investigation.

Findings that cannot be spot-checked get re-derived by hand, which costs more
than the investigation saved.

## Two output modes

-   **Inline (default, during investigation).** Keep the conversational
    register, but every factual claim still carries a citation. Don't build a
    full report for an exploratory answer.
-   **Full report.** Use when presenting a conclusion, recommending a mitigation
    or configuration change, writing a Root Cause Analysis (RCA), or providing
    an official diagnostic writeup.

## Structure: timeline and conclusions

An Executive Summary is fine to include at the top to orient the reader, which
is especially helpful for complex issues.

Following the summary (or starting directly with it for straightforward issues),
provide a chronological timeline of what the system did — one line per observed
event, each with its source, timestamp, and citation. Detailed conclusions and
analysis should follow the timeline.

Conclusions must not introduce facts or observations that aren't established in
the timeline (such as unmentioned log events, metric changes, or state
transitions). If a conclusion needs an observed fact, that fact belongs in the
timeline with a citation.

This structure lets the reader quickly grasp the situation from the summary,
audit the raw sequence in the timeline, and verify that conclusions rest
directly on cited evidence.

## Timestamps: keep the native timezone, label every line

Dataflow investigations mix sources with different clocks (e.g., Cloud Logging
timestamps in local time or UTC, Cloud Monitoring metric series in UTC, and
Dataflow job status events in UTC).

Don't silently normalize or write bare timestamps without their source and
timezone. Every timestamp throughout the entire write-up (in the timeline,
tables, executive summary, and prose) must be explicitly labeled with BOTH its
timezone and its source, e.g. `16:00:00 UTC (Cloud Monitoring)` or `09:15:30 PDT
(Cloud Logging)`. Even when mentioning a timestamp in a sentence (e.g. "stalled
at 16:00 UTC (Cloud Monitoring)"), always include the source name in
parentheses. Never write bare timestamps like `14:54:33` without the source and
timezone.

For customer-impact or performance claims (stall duration, backlog window,
time-to-recover), state start, end, and computed duration explicitly rather than
making the reader subtract.

## Citations

Every factual claim carries at least one of:

-   A deep link to the source UI: Cloud Console Dataflow job page, Cloud
    Monitoring dashboard / Metrics Explorer, or Cloud Logging query URL.
-   A code pointer with line numbers: `file:///path/to/pipeline.py#L123` or
    repository URL.
-   The exact command with all flags and the time window, when the claim came
    from a CLI query (`gcloud`) or REST API call and there's no stable link to
    it.

Quote raw output **verbatim** when the claim depends on the exact text — error
strings, status codes, log lines, metric values. Trim with an ellipsis (`...`);
never reword or paraphrase. A paraphrased error message cannot be searched for
or grepped in logs or code.

Trace every entity — job ID, project ID, region, worker pool, machine type,
step/stage — to the source that asserts it:

-   **Authoritative telemetry beats human reports:** Direct API responses, job
    execution protos, and system log lines are authoritative over pipeline
    descriptions or issue reports typed into tickets (which are often human
    shorthand, mistaken, or misattributed).
-   **Explicitly call out contradictions:** When authoritative telemetry
    disagrees with a user description or ticket note, explicitly state the
    contradiction in your write-up and explain why the telemetry is
    authoritative. Never silently report the corrected entity without noting the
    discrepancy.

## The bar for "X caused Y"

Hold at least **two** of these before writing a causal claim:

1.  A mechanism in the code or architecture that explains how X produces Y, with
    a code or documentation pointer.
2.  Temporal correlation, with the actual time gap stated (not just "right
    after").
3.  A counterfactual: it recovered when X changed, or Y is absent where X is
    absent.
4.  A prior incident, documented issue, or known bug with the same signature and
    a confirmed root cause, cited by ID or link.

With fewer than two, call it a hypothesis and state what evidence would confirm
it. Correlation being the only thing available is not a reason to promote it to
cause.

## The bar for recommending a mitigation

Every mitigation or remediation recommendation must include these four elements:

1.  **Precise target:** Scope the recommendation to the exact failing entity:
    "increase `maxNumWorkers` from 10 to 30 for job `<job_id>` in region
    `us-central1`", or "update transform `ParsePayload` in `pipeline.py#L85`",
    never a blanket "restart the pipeline" or "scale up the project". Blanket
    actions without precise scoping risk unnecessary downtime, unexpected costs,
    or masking underlying data issues.
2.  **Code- or system-level rationale:** Explain why the action clears the
    failing state (e.g., clearing a saturated worker queue, increasing key
    cardinality, or overcoming a throughput quota).
3.  **Precedent evidence:** Cite documentation, a best-practice guide, or a
    prior verified incident where this exact mitigation resolved this exact
    signature.
4.  **Recurrence & root cause warning:** Explicitly state whether this action
    fixes the root cause or is only a temporary mitigation. If the root cause
    remains open (such as an unhandled exception or data skew), warn that the
    failure can recur until the underlying pipeline code or configuration is
    fixed.

If you can't meet the bar, present the action as an option and name the missing
evidence.

## Mark unverified claims inline

Put the gap where the claim is, not in a section at the end the reader reaches
after already believing you:

> Worker `dataflow-job-xyz-worker-1` dropped processing rate (could not verify
> whether VM experienced an OOM: metrics history unavailable for that window).

### Empty query results are not evidence of absence

When a query, log search, or metric query returns zero results:

-   **Explicitly state that zero hits does not prove absence:** Never state or
    advise telling a user or stakeholder that a problem does not affect a
    pipeline, region, or component based on zero query results.
-   **Write "no results from `<query>`"**, never "no problem found" or "the
    pipeline is unaffected".
-   **Explain what it rules out and what it does not rule out:** An empty result
    can be caused by exact-string mismatches, log filtering on the wrong step
    ID, overly narrow time windows, log sampling or retention limits, timezone
    discrepancies, or errors occurring in a different component (e.g., worker
    system logs vs user code logs).
-   **Always explicitly recommend validating the query itself against a known
    positive case:** Test the exact same query against a known affected job,
    stage, or time window where the error is confirmed to have occurred. If the
    query does not return hits on a known positive case, the query itself is
    defective or mis-scoped.
-   **Provide safe phrasing:** Frame updates strictly around verified query
    parameters: *"Searched logs across `<scope>` between `<time_range>` for
    `<signature>` and found zero matching occurrences. We cannot confirm absence
    of the underlying issue without validating the query against an affected
    workload."*

## Self-audit before presenting

You MUST run this self-audit checklist on your generated response before
finalizing.

Run this checklist against your findings before presenting them:

-   [ ] Every factual claim has a deep link, code pointer, or named command.
-   [ ] Every timestamp is labeled with its timezone and source.
-   [ ] Every job ID, project ID, region, and stage traces to an authoritative
    source, and any contradiction with initial user reports is explicitly called
    out and explained.
-   [ ] Causal claims meet the two-of-four bar; everything else is labeled a
    hypothesis with the confirming evidence named.
-   [ ] Any mitigation has a technical rationale, precedent evidence, a precise
    target, and an explicit statement of what it doesn't fix and whether the
    failure can recur.
-   [ ] Unverified claims are marked inline at the point of the claim.
-   [ ] Conclusions introduce no fact that isn't in the timeline.
-   [ ] Empty results are described as "no results from `<query>`", never as "no
    problem found", and include a recommendation to validate the query against
    known positive occurrences.
-   [ ] Irrelevant dead ends are completely omitted rather than listed under a
    dead-ends section.
