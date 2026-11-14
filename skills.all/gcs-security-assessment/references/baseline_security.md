# Baseline Security

Baseline checks are evaluated for **every project and bucket** before toxic
combination analysis begins. These are prerequisites — any single failure is
flagged independently.

> [!IMPORTANT]
> Baseline failures are reported separately from toxic
> combinations. A bucket can fail baseline checks AND match a toxic combination
> archetype. Report both.

## Baseline Controls

Each control below MUST be checked. Reporting rules:

-   **Per-bucket controls (e.g., UBLA):** If passing, do not mention. Only
    report failures. For each failure, the report must include (a) an accurate
    count of affected buckets, and (b) the bucket names — inline if count ≤ 10,
    otherwise the first 10 followed by "... and N more (see telemetry output for
    full list)". Never substitute a vague rollup line for the count.
-   **Project-level controls (Block HTTP, TLS, HMAC, Data Access Audit Logs):**
    Whether passing or failing, surface the state in the Section 2 policy
    summary using ✅ (verified passing) or ❌ (failing). This confirms to the
    admin that the control was actually checked.
-   **Independence:** Each failure is its own finding. Do NOT bundle multiple
    baseline failures into a single toxic-combination archetype label. Reserve
    toxic-combo labels for the named archetypes in
    `references/toxic_combinations.md`.

### UBLA (Bucket-Level)

Secure State      | Vulnerable State
----------------- | -----------------------------------------------------
UBLA is `ENABLED` | UBLA is `DISABLED` — legacy ACLs active alongside IAM

**Why it matters:** When UBLA is disabled, ACLs operate alongside IAM, creating
shadow access paths. A bucket can appear locked down via IAM while an ACL
silently grants public access.

**Remediation:**

-   Enforce Uniform Bucket-Level Access: `gcloud storage buckets update
    gs://BUCKET --uniform-bucket-level-access`

### Block HTTP (Project-Level Org Policy)

Secure State                   | Vulnerable State
------------------------------ | ----------------------------------
Secure transport is `ENFORCED` | Secure transport is `NOT_ENFORCED`

**Why it matters:** Without this policy, data can be transmitted over plaintext
HTTP and intercepted in transit.

**Remediation:**

-   Enforce secure transport via org policy

### TLS Version (Project-Level Org Policy)

Secure State                           | Vulnerable State
-------------------------------------- | -------------------------
Minimum TLS version is `1.2` or higher | TLS 1.0 or 1.1 is allowed

**Why it matters:** TLS 1.0 and 1.1 have known vulnerabilities. Allowing them
means connections can downgrade to insecure versions.

**Remediation:**

-   Enforce minimum TLS 1.2 via org policy

### HMAC Authentication Restriction (Project-Level Org Policy)

Secure State                        | Vulnerable State
----------------------------------- | -------------------------------------
HMAC authentication is `RESTRICTED` | HMAC authentication is not restricted

**Why it matters:** HMAC keys are long-lived static credentials. If a key leaks,
it remains valid until manually revoked. Restricting HMAC forces the use of
short-lived OAuth/OIDC tokens.

**Remediation:**

-   Restrict HMAC authentication via org policy
    (`constraints/storage.restrictAuthTypes`)

### Data Access Audit Logging (Project-Level)

| Secure State                         | Vulnerable State          |
| ------------------------------------ | ------------------------- |
| DATA_READ and DATA_WRITE enabled for | Data Access logs disabled |
: `storage.googleapis.com`             :                           :

**Why it matters:** Without Data Access audit logs, reads, writes, and deletions
leave no forensic trail. Exfiltration, tampering, and unauthorized access are
invisible.

**Remediation:**

-   Enable Data Access audit logs: Update project audit config for
    `storage.googleapis.com` with DATA_READ and DATA_WRITE. Scope to high-value
    buckets. Set log retention policies and restrict IAM on log sinks to prevent
    audit logs from becoming a secondary exposure.

> [!TIP]
> Data Access audit logs can generate high volume on busy buckets.
> Recommend scoping to high-value buckets rather than enabling project-wide.
