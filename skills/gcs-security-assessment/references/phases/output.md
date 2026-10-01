# Phase 5: Output

Present your assessment in a scannable, action-oriented format.

## Goal

The target user is a Storage Admin with limited security expertise who needs to
quickly understand: what's wrong, how bad is it, and how to fix it. They may
action remediations via the Cloud Console (Pantheon) or gcloud CLI — both paths
should be clear.

## Output Structure

**Section 1: Risk Heuristic**

Outline the overall bucket security risk score with a short explanation.

Example:

Bucket Security Risk Heuristic: xx/100

Risk score is a heuristic determined in aggregate meant to estimate the overall
risk level across all buckets in a project based off some of the criteria
described below. Remediation of these steps will reduce the risk score, though a
risk score of 0 does not necessarily mean the project is 100% without risk.

**Section 2: Risk Dashboard**

A table of the top 5 riskiest buckets (sorted by severity), followed by a
policy-level control status block and per-control bucket rollups. The admin
should understand their overall risk posture from this section alone.

Table columns: Priority (#), Bucket, Severity, Risk, Quickfix.

**Risk column content:**

-   If the bucket matches a named toxic-combination archetype from
    `references/toxic_combinations.md`, the Risk cell contains that archetype
    name (e.g., "Public Data Pipeline", "Prompt Injection to Data Destruction").
-   Otherwise — the bucket fails only baseline controls — the Risk cell
    enumerates the failing baseline controls separated by semicolons (e.g.,
    "UBLA disabled; versioning off"). Do NOT invent a toxic-combo-style label
    for baseline-only failures.

Example:

| \# | Bucket | Severity | Risk | Quickfix | | -- | ----------------------
| -------- | -------------------------------------
| ----------------------------------- | | 1 | gs://training-datasets | Critical
| Public Data Pipeline | Block public access → Bucket Fix #1 | | 2 |
gs://model-checkpoints | Critical | Prompt Injection to Data Destruction | See
Policy Fix #2, Bucket Fix #2 | | 3 | gs://logs-archive | Medium | UBLA disabled;
versioning off | See Bucket Fix #2, Bucket Fix #3 |

Follow the table with a policy-level summary and a baseline-failure rollup:

```
✅ Verified: HMAC restriction, Data Access Audit Logs
❌ Policy gaps: restrictTLSVersion not enforced
   Why: TLS 1.0/1.1 have known vulnerabilities; allowing them lets connections downgrade to insecure versions.
❌ Policy gaps: secureHttpTransport not enforced
   Why: Without this policy, data can be transmitted over plaintext HTTP and intercepted in transit.
❌ UBLA disabled (10): gs://a, gs://b, gs://c, gs://d, gs://e, gs://f, gs://g, gs://h, gs://i, gs://j
   Why: Legacy ACLs operate alongside IAM, creating shadow access paths. A bucket can appear locked down via IAM while an ACL silently grants public access.
⚠️  2 buckets unclassified; sensitivity unknown, risk scores inferred
```

Rules for these lines:

-   **Project-level controls:** Always surface every baseline project-level
    control here — ✅ for verified-passing, ❌ for failing. Emit a separate ❌ line
    with a unique `Why:` caption for EACH failing project-level control. Do NOT
    merge multiple failing policies into a single line. This confirms to the
    admin the control was actually evaluated.
-   **Per-control bucket rollup (MANDATORY for every per-bucket baseline that
    has at least one failing bucket):** For each failing per-bucket baseline
    control — UBLA, object versioning, soft delete, etc. — emit one line in
    Section 2 with an accurate count of affected buckets and the bucket names.
    If count ≤ 10, list inline. If > 10, list the first 10 followed by "... and
    N more (full list in telemetry output)". Never replace the count with a
    vague rollup like "X additional buckets assessed — no critical findings."
    Section 3 per-bucket cards do NOT substitute for this rollup: a baseline
    failure that appears in a per-bucket card must still appear in the Section 2
    rollup. Failures missing from Section 2 are treated as missing findings.
-   **Why caption (required for every ❌ baseline failure):** Each ❌ line —
    whether project-level or per-bucket — must be followed by a one-line `Why:`
    caption that explains the risk. Pull the caption from the matching control's
    "Why it matters" paragraph in `references/baseline_security.md` and condense
    to one sentence. Examples: for UBLA disabled, cite legacy-ACL shadow access
    paths bypassing IAM; for TLS, cite downgrade-to-insecure-version risk; for
    versioning, cite irreversible overwrite/delete; for audit logs, cite missing
    forensic trail. Do NOT add a Why caption for ✅ verified-passing lines.
-   **Unclassified / informational:** Use ⚠️ for caveats that don't fit ✅/❌.

**Section 3: Action Plan**

Start with the per-bucket cards so the admin sees the findings before the fixes.
Follow with Policy Fixes and Bucket Fixes as a remediation reference.

**Per-Bucket Cards** (soft cap: 6 lines per card):

```
gs://bucket-name  [Severity · Toxic Combination Label]
One sentence explaining the attack path or failure mode.
❌ Control: status  ❌ Control: status  ✅ Control: status  ⚠️ Control: note
❌ Control: status  ❌ Control: status
1. What is being fixed: → Bucket Fix #1
2. What is being fixed: → Policy Fix #2
```

Line 1: bucket name + severity + risk label. The risk label must be either (a)
one of the named toxic-combination archetypes from
`references/toxic_combinations.md` (Public Data Pipeline, Silent Data Theft,
Irreversible Data Corruption, Intentional Public Data, Compliance Without Proof,
Prompt Injection to Data Destruction) if the bucket matches one, or (b) the
literal string "Baseline failures" when the bucket fails only baseline controls
and matches no archetype. Do not invent new archetype-style names. Line 2: one
sentence — the "so what" for a busy admin Lines 3–4: all relevant control
statuses on 1–2 lines (omit passing controls unless they create false confidence
— use ⚠️ for those) Lines 5–6: remediation steps referencing fix IDs; never
repeat a command inline if it is already defined in the fix list

Example card:

```
gs://training-datasets  [Critical · Public Data Pipeline]
Publicly readable, no encryption. Exfiltration leaves no recovery path.
❌ Public: allUsers objectViewer  ❌ Encryption: Google-default  ❌ VPC-SC: None
✅ UBLA  ⚠️ Soft Delete: Enabled but no versioning (incomplete recovery)
1. Remove unauthenticated read access: → Bucket Fix #1
2. Add encryption and network boundary: → Bucket Fix #1 (CMEK), Policy Fix #2
```

**Policy Fixes** (org or project-level — may require elevated permissions):

List each fix with a title, Console path, and gcloud command. Only include a
description when the fix title alone is not self-explanatory.

```
Policy Fix #1. Enforce HTTPS-only access
               Console: IAM & Admin > Organization Policies > constraints/storage.secureHttpTransport
               gcloud: gcloud org-policies set-policy policy.yaml --project=PROJECT_ID

Policy Fix #2. Enforce minimum TLS 1.2
               Console: IAM & Admin > Organization Policies > constraints/gcp.restrictTLSVersion
               gcloud: gcloud org-policies set-policy policy.yaml --project=PROJECT_ID

Policy Fix #3. Restrict HMAC authentication
               Console: IAM & Admin > Organization Policies > constraints/storage.restrictAuthTypes
               gcloud: gcloud org-policies set-policy policy.yaml --project=PROJECT_ID

Policy Fix #4. Enable Data Access audit logs
               Console: IAM & Admin > Audit Logs > Cloud Storage > Enable DATA_READ and DATA_WRITE
               gcloud: Update project audit config for storage.googleapis.com with DATA_READ and DATA_WRITE

Policy Fix #5. Enroll in VPC-SC perimeter
               Console: Security > VPC Service Controls > New Perimeter
```

**Bucket Fixes** (bucket-level — can be applied directly by a Storage Admin):

```
Bucket Fix #1. Apply customer-managed encryption (CMEK): replaces Google-default
               encryption with a key you control, enabling cryptographic revocation.
               Console: Cloud Storage > Bucket > Configuration > Encryption > Customer-managed key
               gcloud: gcloud storage buckets update gs://BUCKET --default-kms-key=KEY

Bucket Fix #2. Enable object versioning
               Console: Cloud Storage > Bucket > Protection > Object versioning > Enable
               gcloud: gcloud storage buckets update gs://BUCKET --versioning
```

## Project-only mode

If preflight returned `analysis_scope: project_only` (Storage Intelligence
unavailable), you have project-level signals but no per-bucket or per-object
telemetry. Adapt the structure above:

-   Open with a one-line note that this is a **project-level assessment** and a
    recommendation to enable Storage Intelligence to unlock the full bucket- and
    object-level assessment (relay the preflight `fix` verbatim).
-   **Skip** the bucket Risk Heuristic (Section 1) and the per-bucket Risk
    Dashboard table (Section 2's bucket rows) — render them as "Unavailable —
    requires Storage Intelligence" rather than fabricating buckets or scores.
-   **Keep** the policy-level control status block and project findings: IAM,
    VPC-SC, Data Access audit logs, org policies (data residency, Block HTTP,
    TLS floor, HMAC), and Model Armor posture. These carry the report.

## Important Rules

-   Limit per-bucket *cards* (Section 3) to the top 5 riskiest buckets. Buckets
    with baseline failures outside the top 5 are still surfaced in the Section 2
    per-control rollup lines (with accurate counts and names per the rules
    above), so no bucket with a finding is silently dropped. Do NOT use a
    generic "X additional buckets — no critical findings" tail; if the remaining
    buckets have findings, those findings are already represented in the Section
    2 rollup.
-   Baseline failures are enumerated as discrete items, not collapsed into a
    single toxic-combination archetype label. Toxic-combo labels are reserved
    for the named archetypes in `references/toxic_combinations.md`.
-   **UNKNOWN signals must be reported consistently across the entire report.**
    When a signal is unverifiable (e.g., VPC-SC because the caller lacks
    `accesscontextmanager.policies.list`, audit log status because of a missing
    permission), every mention of that signal — narrative summaries, "Key
    Findings" / "Assessment Summary" prose, Section 2 lines, Section 3
    per-bucket cards, fixes — must reflect UNKNOWN (or equivalent: "Access
    Denied", "permission denied", "status not verifiable"). Do NOT infer
    "missing", "lacking", "not configured", "not enforced", or any equivalent
    state in any section. An UNKNOWN signal anywhere is UNKNOWN everywhere.
-   Show findings (bucket cards) before fixes. Admins should understand the
    problem before looking up the remediation.
-   Never repeat a command under multiple bucket cards. Define it once in Policy
    Fixes or Bucket Fixes and reference it by ID.
-   Only include a description on a fix when the title alone is not
    self-explanatory (e.g., CMEK warrants a note; "Block public access" does
    not).
-   Where a fix can be applied via Console, include the Console path. gcloud is
    secondary, not the only option.
-   One sentence max for the danger explanation per card. No academic prose.
-   Use ⚠️ (not ✅) for controls that pass but create false confidence, with a
    brief inline note explaining why.
-   The Quickfix column in Section 2 should be a short plain-language label +
    fix reference — never just a raw command, never blank.

> [!TIP]
> See `examples/sample_assessment.md` for a complete example of expected
> output format.
