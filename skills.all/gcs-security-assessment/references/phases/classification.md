# Phase 2: Bucket Classification

Before evaluating security posture, classify each bucket's data sensitivity.

## Instructions

Follow the classification logic in `references/bucket_classification.md`.

The classification determines how urgently findings should be treated:

-   **High sensitivity** → Full severity on all findings
-   **Medium sensitivity** → Reduced severity
-   **Low sensitivity** → Significantly reduced severity
-   **Non-sensitive (explicit)** → Minimal severity
-   **Unclassified** → Treat as potentially sensitive (full severity)

> [!IMPORTANT]
> Unclassified is NOT the same as non-sensitive. If a bucket has no
> classification, treat it as worst-case until the customer classifies it.
