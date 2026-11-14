# Sample Assessment Output

This is an example of the output format the skill should produce. Adapt the
content to match actual telemetry findings, but follow this structure exactly.

--------------------------------------------------------------------------------

## Security Posture Assessment: ml-platform-prod-101

### Section 1: Risk Heuristic

Bucket Security Risk Heuristic: 10/100

Risk score is a heuristic determined in aggregate meant to estimate the overall
risk level across all buckets in a project based off some of the criteria
described below. Remediation of these steps will reduce the risk score, though a
risk score of 0 does not necessarily mean the project is 100% without risk.

### Section 2: Risk Dashboard

| \# | Bucket | Severity | Risk | Quickfix | | -- | ----------------------
| -------- | ------------------------------------
| --------------------------------- | | 1 | gs://training-datasets | Critical |
Public Data Pipeline | Block public access → B1, B2 | | 2 |
gs://model-checkpoints | Critical | Prompt Injection to Data Destruction | Fix
Model Armor + scope SA → B6, B7 | | 3 | gs://public-api-docs | Low | Intentional
Public Data | Enable recovery controls → B4, B5 | | 4 | gs://logs-archive |
Medium | UBLA disabled; versioning off | See B2, B5 |

```
✅ Verified: HMAC restriction, TLS 1.2 minimum
❌ Policy gaps: Block HTTP not enforced
   Why: Without this policy, data can be transmitted over plaintext HTTP and intercepted in transit.
❌ Policy gaps: Data Access Audit Logs not enabled
   Why: Without Data Access logs, reads/writes/deletions leave no forensic trail; exfiltration and tampering are invisible.
❌ UBLA disabled (4): gs://training-datasets, gs://logs-archive, gs://temp-uploads, gs://snapshot-2024
   Why: Legacy ACLs operate alongside IAM, creating shadow access paths. A bucket can appear locked down via IAM while an ACL silently grants public access.
❌ Object versioning disabled (3): gs://training-datasets, gs://model-checkpoints, gs://logs-archive
   Why: Without versioning, overwrites and deletes are irreversible; one bad client or compromised credential can permanently destroy data.
⚠️  VPC-SC status: Unknown (caller lacks accesscontextmanager.policies.list)
⚠️  2 buckets unclassified; sensitivity inferred, run SDP to confirm
```

--------------------------------------------------------------------------------

### Section 3: Action Plan

```
gs://training-datasets  [Critical · Public Data Pipeline]
Unclassified training data is public. Exfiltration is silent with no audit trail.
❌ UBLA: Disabled (ACLs bypass IAM)  ❌ Public: allUsers READER  ❌ Encryption: Google-default  ❌ VPC-SC: None
❌ Soft Delete: Off  ❌ Versioning: Off  ❌ Audit Logs: Off
1. Close public access and shadow ACL path: → B1, B2
2. Add encryption, recovery, network, and logging: → B3, B4, B5, P1, P2
```

```
gs://model-checkpoints  [Critical · Prompt Injection to Data Destruction]
Admin SA + inactive Model Armor: one injection can destroy all checkpoints.
⚠️ Model Armor: API enabled but Vertex AI integration inactive (not enforced)
⚠️ IAM: agent-sa holds roles/storage.admin  ❌ Versioning: Off  ❌ VPC-SC: None
1. Neutralize agent takeover path: → B6 (scope SA), B7 (activate Model Armor)
2. Add encryption, recovery, network: → B3, B4, B5, P1, P2
```

```
gs://public-api-docs  [Low · Intentional Public Data]
Intentional public bucket: without versioning, content can be defaced permanently.
✅ UBLA  ✅ Public Access: Intentional (tagged purpose:public-documentation)
❌ Soft Delete: Off  ❌ Versioning: Off
1. Add integrity and recovery protection: → B4 (soft delete), B5 (versioning)
NOTE: Public access is intentional; no access control changes recommended.
```

```
gs://logs-archive  [Medium · Baseline failures]
Legacy ACLs are active and there is no version history if objects are overwritten.
❌ UBLA: Disabled (ACLs bypass IAM)  ❌ Versioning: Off
1. Enforce UBLA and recovery: → B2 (UBLA), B5 (versioning)
```

--------------------------------------------------------------------------------

**Policy Fixes** (org or project-level — may require elevated permissions):

```
P1. Enable Data Access audit logs
    Console: IAM & Admin > Audit Logs > Cloud Storage > Data Read + Data Write
    gcloud: Update project audit config for storage.googleapis.com with DATA_READ and DATA_WRITE

P2. Enroll in VPC-SC perimeter
    Console: Security > VPC Service Controls > New Perimeter
    gcloud: gcloud access-context-manager perimeters create ml-perimeter --title='ML Platform Perimeter' --resources=projects/101202303404 --restricted-services=storage.googleapis.com,aiplatform.googleapis.com --policy=POLICY_ID

P3. Enforce HTTPS-only access
    Console: IAM & Admin > Organization Policies > constraints/storage.secureHttpTransport
    gcloud: gcloud org-policies set-policy policy.yaml --project=ml-platform-prod-101
```

**Bucket Fixes** (bucket-level — can be applied directly by a Storage Admin):

```
B1. Block public access
    Console: Cloud Storage > Bucket > Permissions > Remove allUsers
    gcloud: gcloud storage buckets update gs://training-datasets --public-access-prevention

B2. Enable Uniform Bucket-Level Access (UBLA)
    Console: Cloud Storage > Bucket > Configuration > Access control > Uniform
    gcloud: gcloud storage buckets update gs://training-datasets --uniform-bucket-level-access

B3. Apply customer-managed encryption (CMEK): replaces Google-default encryption
    with a key you control, enabling cryptographic access revocation in an emergency.
    Console: Cloud Storage > Bucket > Configuration > Encryption > Customer-managed key
    gcloud: gcloud storage buckets update gs://BUCKET --default-kms-key=KEY

B4. Enable soft delete
    Console: Cloud Storage > Bucket > Protection > Soft delete policy > Enable
    gcloud: gcloud storage buckets update gs://BUCKET --soft-delete-duration=7d

B5. Enable object versioning
    Console: Cloud Storage > Bucket > Protection > Object versioning > Enable
    gcloud: gcloud storage buckets update gs://BUCKET --versioning

B6. Reduce agent SA to least privilege: removes project-wide storage.admin and
    replaces it with bucket-scoped read-only, blocking the agent takeover path.
    Console: Cloud Storage > Bucket > Permissions > Edit agent SA role
    gcloud: gcloud projects remove-iam-policy-binding ml-platform-prod-101 --member='serviceAccount:AGENT_SA' --role='roles/storage.admin'
            gcloud storage buckets add-iam-policy-binding gs://model-checkpoints --member='serviceAccount:AGENT_SA' --role='roles/storage.objectViewer'

B7. Activate Model Armor Vertex AI integration: wires prompt screening into
    Gemini calls so injections are blocked before reaching the agent.
    Console: Model Armor > Floor Settings > Integrated Services > Enable Vertex AI
    gcloud: gcloud model-armor floorsettings update --full-uri=projects/PROJECT_ID/locations/global/floorSetting --add-integrated-services=VERTEX_AI --vertex-ai-enforcement-type=INSPECT_AND_BLOCK
```
