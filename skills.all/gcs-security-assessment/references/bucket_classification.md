# Bucket Classification

Classification runs in Phase 2, before any security evaluation. It determines
the sensitivity context that modulates how urgently findings are treated.

> [!IMPORTANT]
> Classification does NOT change which controls are recommended.
> The same controls apply regardless of sensitivity. Classification only
> modulates the severity label.

## Step 1: Check for Existing Classification

Check whether the bucket has sensitivity labels from any of these sources:

### Source A: SDP (Sensitive Data Protection) Results

If SDP has scanned the bucket, use the SDP-assigned tier as **authoritative**:

-   **High**: PII, financial records, healthcare data, credentials detected
-   **Medium**: Internal business data, proprietary content, limited PII
    detected
-   **Low**: SDP scanned and found no significant sensitive content

### Source B: Customer Tags or Labels

If the bucket has customer-applied tags (e.g., `sensitivity:high`,
`data-type:training`), derive a sensitivity tier using the SDP mapping table.
Customer tags are treated as equivalent to SDP classification — do NOT penalize
customers for using tags instead of SDP.

### Source C: Unclassified

No labels, no tags, no SDP scan. This is the default state for most buckets.

## Step 2: Handle Unclassified Buckets

For unclassified buckets, do two things:

**First**, infer a provisional sensitivity estimate from heuristics:

| Heuristic                           | Suggests Higher Sensitivity          |
| ----------------------------------- | ------------------------------------ |
| Bucket name contains `prod`,        | Yes                                  |
: `training`, `ml`, `model`,          :                                      :
: `weights`, `pii`, `financial`,      :                                      :
: `health`                            :                                      :
| Bucket name contains `test`, `dev`, | No                                   |
: `sandbox`, `tmp`, `public`,         :                                      :
: `static`, `assets`                  :                                      :
| Encryption type is CMEK or CSEK     | Yes — customer invested in key       |
:                                     : management                           :
| Project also contains Vertex AI     | Yes — likely AI workload data        |
: endpoints or Agent Engine           :                                      :
| Large object count or total size    | Weakly yes — significant data stores |
:                                     : tend to matter more                  :

**Second**, surface this recommendation in your output:

> This bucket has no sensitivity classification. Run Sensitive Data Protection
> to classify the contents and enable more accurate risk scoring. Until
> classified, this bucket is treated as potentially sensitive.

Flag the provisional estimate as **"inferred — not verified"** in all output.

## Step 3: Modulate Severity

Use the classification to adjust the severity label for each finding:

| Classification          | Severity Modulation   | Rationale                |
| ----------------------- | --------------------- | ------------------------ |
| High (SDP or            | Full severity         | Confirmed sensitive,     |
: customer-tagged)        :                       : maximum urgency          :
| Medium (SDP or          | Reduced severity      | Moderate sensitivity,    |
: customer-tagged)        :                       : still significant        :
| Low (SDP or             | Significantly reduced | Verified low-sensitivity |
: customer-tagged)        : severity              : content                  :
| Non-sensitive           | Minimal severity      | Customer affirmed        |
: (explicitly tagged)     :                       : non-sensitive            :
| Unclassified (inferred) | Full severity         | Unknown = potentially    |
:                         :                       : sensitive, worst case    :

> [!CAUTION]
> **Unclassified is NOT non-sensitive.** Unknown data gets full
> severity because you cannot confirm it is safe. Only an affirmative
> classification (SDP or explicit customer tag) reduces severity.

## Exception: Classification Mismatch

If a bucket is classified as **High sensitivity** but also has **public access
enabled**, do NOT treat this as Intentional Public Data. Flag it as a potential
misconfiguration:

> **ALERT: Classification Mismatch.** This bucket is classified as
> high-sensitivity but is publicly accessible. Verify whether public access is
> intentional. If not, this is a critical exposure requiring immediate
> remediation.
