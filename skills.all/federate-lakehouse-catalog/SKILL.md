---
name: federate-lakehouse-catalog
description: >-
  Sets up Google Cloud Lakehouse federated catalogs to remote Iceberg REST Catalogs. Currently supported catalogs: Databricks Unity, AWS Glue. Supported clouds hosting those catalogs: GCP, AWS. The primary use case is connecting to remote data to query it from GCP engines (BigQuery, Spark). Examples of when to use this: "federate my lakehouse catalog to databricks", "query data in databricks", "query data in s3", "connect to aws glue". Do NOT use for direct remote database SQL execution (e.g., Databricks SQL) or managing remote clusters and infrastructure (e.g., Databricks clusters, AWS Glue jobs).
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# Federate Lakehouse Catalog via Cross-cloud Lakehouse

This skill describes how to set up a federated catalog in BigQuery to query
remote catalogs like Databricks Unity Catalog or AWS Glue Data Catalog data in
AWS over the public internet.

## Prerequisites

-   For Databricks: Databricks Workspace URL and OAuth Service Principal (Client
    ID and Secret) with read access.
-   For AWS Glue: AWS Administrator access to create IAM roles and permissions
    policies.
-   Active Google Cloud project with administrative access to create lakehouse
    resources, and secrets in the case of Databricks.

## Procedure

### Step 1: Information Gathering and Region Selection

Before running any commands, the agent **MUST** collect the following
information from the user:

1.  Determine which catalog the user wants to federate to (e.g., Databricks
    Unity or AWS Glue) and verify it is supported.
2.  Determine where the remote data is located (the specific AWS region).
3.  Using the Region Pairing Best Practice in the Gotchas section, help the user
    pick the optimal GCP region to minimize latency.
4.  Collect the necessary configuration variables for the chosen flow (e.g.,
    Databricks credentials or AWS Account ID).

Only proceed to the next steps once this information is confirmed.

### Step 2: API Verification

Verify that the required Google Cloud APIs are enabled for the project:

```bash
gcloud services check biglake.googleapis.com
```

If the API is not enabled, explicitly ask the user for permission to enable it.
Do NOT proceed without their confirmation.

### Flow A: Databricks Unity Catalog

#### 1. Create a Regional Secret for Credentials

Store the Databricks client ID and secret in Secret Manager. Ensure the
`secretmanager.googleapis.com` API is enabled. The secret **MUST** be in the
same region as your Lakehouse catalog.

1.  Create a JSON file named `credentials.json`:

```json
{
  "client_id": "<CLIENT_ID>",
  "client_secret": "<CLIENT_SECRET>"
}
```

1.  Set the Secret Manager API endpoint override for the region:

```bash
gcloud config set api_endpoint_overrides/secretmanager https://secretmanager.<REGION>.rep.googleapis.com/
```

1.  Create the secret:

```bash
gcloud secrets create <SECRET_NAME> \
  --location="<REGION>" \
  --project="<PROJECT_ID>" \
  --data-file=credentials.json
```

#### 2. Create the Federated Catalog

Create a BigLake Iceberg catalog of type `federated` pointing to Databricks.

```bash
gcloud alpha biglake iceberg catalogs create <CATALOG_NAME> \
   --project="<PROJECT_ID>" \
   --primary-location="<REGION>" \
   --catalog-type="federated" \
   --federated-catalog-type="unity" \
   --secret-name="projects/<PROJECT_ID>/locations/<REGION>/secrets/<SECRET_NAME>" \
   --unity-instance-name="<UNITY_INSTANCE_NAME>" \
   --unity-catalog-name="<UNITY_CATALOG_NAME>" \
   --refresh-interval="300s"
```

#### 3. Grant Catalog Access to the Secret

Grant the service account created for the catalog access to read the secret.

1.  Get the service account email by describing the catalog:

```bash
gcloud alpha biglake iceberg catalogs describe <CATALOG_NAME> \
    --project="<PROJECT_ID>" \
    --location="<REGION>" \
    --format="value(biglake-service-account-id)"
```

1.  Grant access:

```bash
gcloud secrets add-iam-policy-binding <SECRET_NAME> \
  --project="<PROJECT_ID>" \
  --location="<REGION>" \
  --member="serviceAccount:<SERVICE_ACCOUNT_EMAIL>" \
  --role="roles/secretmanager.secretAccessor"
```

### Flow B: AWS Glue

#### 1. Create the AWS IAM role with a placeholder trust policy

Lakehouse provisions a Google service account ID after catalog creation. Create
the AWS IAM role with a placeholder trust policy first.

1.  Create a file named `trust_policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "accounts.google.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "accounts.google.com:aud": ["PLACEHOLDER_VALUE"],
          "accounts.google.com:sub": ["PLACEHOLDER_VALUE"]
        }
      }
    }
  ]
}
```

1.  Run the AWS CLI command to create the role:

```bash
aws iam create-role \
  --role-name <AWS_ROLE_NAME> \
  --assume-role-policy-document file://trust_policy.json \
  --max-session-duration 43200
```

#### 2. Attach a permissions policy

Attach a policy that allows Lakehouse to read from Glue and S3.

> [!IMPORTANT] **Safe IAM Scoping**: The example below uses wildcard structures
> for illustration. You **MUST** consult with the user to scope the `Resource`
> ARNs to their specific catalog, database, and S3 buckets. Do NOT blindly apply
> wildcard permissions.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GlueRead",
      "Effect": "Allow",
      "Action": [
        "glue:GetCatalog",
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:GetTable",
        "glue:GetTables"
      ],
      "Resource": "arn:aws:glue:<AWS_REGION>:<AWS_ACCOUNT_ID>:catalog"
    },
    {
      "Sid": "S3Read",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::<SPECIFIC_BUCKET>",
        "arn:aws:s3:::<SPECIFIC_BUCKET>/*"
      ]
    }
  ]
}
```

Attach this permissions policy to your IAM role.

#### 3. Create the Federated Catalog

When creating an AWS Glue federated catalog, the `--glue-warehouse` **MUST** be
set to your 12-digit AWS Account ID string (not an S3 bucket URI). **Best
Practice**: Initialize the catalog without specifying a refresh schedule to
prevent premature metadata synchronization failures while AWS trust
relationships are propagating.

```bash
gcloud alpha biglake iceberg catalogs create <CATALOG_NAME> \
  --project="<PROJECT_ID>" \
  --primary-location="<REGION>" \
  --catalog-type="federated" \
  --federated-catalog-type="glue" \
  --glue-warehouse="<AWS_ACCOUNT_ID>" \
  --glue-aws-region="<AWS_REGION>" \
  --glue-aws-role-arn="arn:aws:iam::<AWS_ACCOUNT_ID>:role/<AWS_ROLE_NAME>"
```

#### 4. Update the trust policy

Extract the `biglake-service-account-id` from the created catalog, and update
your AWS IAM role's trust policy to replace `PLACEHOLDER_VALUE` in the `aud` and
`sub` conditions with this Google Service Agent ID.

#### 5. Enable background refresh

Update the catalog to activate background refresh once the trust policy is
updated.

```bash
gcloud alpha biglake iceberg catalogs update <CATALOG_NAME> \
  --project="<PROJECT_ID>" \
  --refresh-interval="300s"
```

### Querying the Data

Once set up, you can query the tables via BigQuery.

```sql
SELECT * FROM `<PROJECT_ID>.<CATALOG_NAME>.<NAMESPACE>.<TABLE_NAME>` LIMIT 10;
```

## Gotchas and Pitfalls

> [!IMPORTANT] **Regional Isolation**: The Secret Manager secret and the
> Lakehouse catalog **MUST** be created in the exact same region.

> [!TIP] **Region Pairing Best Practice**: When setting up the federated
> catalog, choose GCP regions with "Low Latency Dedicated" or "Partner CCI" to
> ensure optimal performance when federating large datasets across clouds.
> Examples of optimal pairings: - AWS `us-east-1` (N. Virginia) pairs best with
> GCP `us-east4` (Ashburn, VA) - AWS `us-west-2` (Oregon) pairs best with GCP
> `us-west1` (The Dalles, OR) - AWS `eu-west-2` (London) pairs best with GCP
> `europe-west2` (London) - AWS `eu-central-1` (Frankfurt) pairs best with GCP
> `europe-west3` (Frankfurt) For the exhaustive list of mappings, read the full
> capabilities table at:
> https://docs.cloud.google.com/lakehouse/docs/regions-capabilities-cross-cloud-lakehouse

> [!IMPORTANT] **BigQuery Query Location**: When querying the federated catalog
> via BigQuery, you **MUST** ensure the query runs in the same region as the
> catalog (e.g., `us-east4`). If using the `bq` CLI, use the `--location` flag.

## Step 3: Validation and Next Steps

After completing the setup, the agent **MUST** validate that the federation is
working and propose next steps to the user.

1.  **Validate the Connection**:

    -   Attempt to list the namespaces or tables in the newly federated catalog
        using the `bq` CLI or BigQuery API. For example:

        ```bash
        bq ls --location="<REGION>" <PROJECT_ID>.<CATALOG_NAME>
        ```

    -   If the command returns a list of namespaces/schemas, the federation is
        successful.

2.  **Troubleshooting**:

    -   If the validation fails (e.g., permission errors, empty results,
        timeout), the agent should consult the Cross-Cloud Lakehouse
        Troubleshooting documentation:
        https://docs.cloud.google.com/lakehouse/docs/troubleshooting.
    -   For AWS Glue, verify that the trust policy correctly references the
        `biglake-service-account-id` and that the GCP and AWS regions match your
        configuration.
    -   For Databricks, verify that the secret exists in the correct region and
        the service account has `roles/secretmanager.secretAccessor`.

3.  **Explore and Propose**:

    -   Assuming the federation is working, browse the available namespaces and
        a few key tables.
    -   Summarize to the user what kind of data was found (e.g., "I see you have
        tables related to e-commerce transactions and customer profiles").
    -   Propose a business or analytical question to the user that would result
        in a meaningful query of their data (e.g., "Would you like me to write a
        query to find the top 5 purchasing customers from last month?").
