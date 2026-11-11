---
name: cloud-databases-onboarding
description: >-
  Guides users through discovering their database requirements, recommends a
  Google Cloud database product or migration destination based on a recommendation
  matrix, and assists in database creation. Use when a user asks 'What database
  service should I use?', 'Help me pick a database', asks which Google Cloud
  database to migrate or onboard a workload to, or wants to create a new database
  on Google Cloud. Don't use for general Google Cloud maintenance, managing
  existing databases, or troubleshooting active Database Migration Service (DMS) jobs.
license: Apache-2.0
metadata:
  version: v2
  publisher: google
  category: Databases
---

# Google Cloud Database Onboarding Skill

This skill provides domain instructions, decision matrices, and
Infrastructure-as-Code workflows to guide users through discovering their exact
database requirements, selecting an optimal Google Cloud database service, and
drafting starter resource provisioning code for user review.

## Progressive Disclosure

*   **Reading / Progressive Disclosure:** When interacting with a user during a
    conversation, load reference files progressively. Follow the Just-in-Time
    (JiT) loading instructions outlined in the phases below.

--------------------------------------------------------------------------------

## Workflow & Just-in-Time (JiT) Instructions

This workflow operates in three distinct sequential phases. Evaluate the active
conversation history to determine the current phase and follow the corresponding
instructions:

### Phase 1: Requirement Discovery & Information Gathering

When a user asks `"What database should I use?"` or requires guidance on Google
Cloud database selection without providing sufficient source or workload
context, you must initiate the Discovery phase.

1.  **Load Discovery Instructions (JiT):** Read the complete contents of
    `references/onboarding_prompts.md` using `view_file`.
2.  **Execute Discovery:** Optionally check `get_active_gcp_connection` and
    `get_active_editor_context` (when available in the IDE) to prefill context,
    and follow the detailed Phase 1 instructions in `onboarding_prompts.md` to
    gather core requirements (data model, workload, scale, and migration
    context) using user-friendly phrasing and enforcing constraints (such as the
    90% confidence rule) before proposing any recommendation.

### Phase 2: Recommendation Analysis & Matrix Consultation

Once you have gathered sufficient explicit discovery context, you must determine
the optimal Google Cloud database recommendation.

1.  **Consult Matrix & Formulate Recommendation (JiT):** Follow the Phase 2
    instructions in `references/onboarding_prompts.md` (or, when the user's
    prompt already specifies the source database and workload requirements, skip
    reading `references/onboarding_prompts.md` and read only the matching source
    section in `references/recommendation_matrix.txt` via `view_file`
    `StartLine`/`EndLine` — MySQL: `44-118`, PostgreSQL: `119-236`, SQL Server:
    `237-305`, Oracle: `306-463`, HBase/DynamoDB/Cassandra: `464-616`,
    Redis/Valkey/Memcached/Aerospike: `617-751`, MongoDB/DocumentDB/CosmosDB:
    `752-797`, Neo4j/Neptune/Graph: `798-836` — to formulate a single primary
    recommendation).
2.  **Deliver Recommendation:** Deliver the recommendation to the user, mapping
    destination codes to plain English, explaining the reasoning, and offering
    to help with provisioning.

### Phase 3: Implementation & Provisioning (Plan-Validate-Execute Pattern)

When the user accepts the recommendation and requests to provision or modify
cloud resources, you must initiate the Implementation & Provisioning phase.

1.  **Load Provisioning Instructions (JiT):** Read the Phase 3 section of
    `references/onboarding_prompts.md` (if not already loaded) using
    `view_file`.
2.  **Execute Plan-Validate-Execute Workflow:** Follow the detailed Phase 3
    instructions in `references/onboarding_prompts.md` to analyze the workspace,
    confirm target file paths with the user, draft and validate Terraform or
    `gcloud` provisioning scripts according to the required formatting and
    tagging rules, and prepare a Change List (CL) or Pull Request for user
    review without applying live infrastructure changes directly.

--------------------------------------------------------------------------------

## Supporting Resources & Documentation

-   [Onboarding Prompts & Phase Rules](references/onboarding_prompts.md)
-   [Database Recommendation Matrix](references/recommendation_matrix.txt)
-   [Google Cloud Databases Overview](https://cloud.google.com/products/databases)
-   [Google Cloud SDK (gcloud) Reference](https://cloud.google.com/sdk/gcloud/reference)
