# Bigtable Infrastructure and Administration

This document provides patterns for provisioning and managing Bigtable
resources.

## Table of Contents

*   [Tooling Split](#tooling-split)
*   [Control Plane (gcloud)](#control-plane-gcloud)
*   [Data Plane (cbt)](#data-plane-cbt)
*   [Observability and Performance](#observability-and-performance)
*   [Local Development (Emulator)](#local-development-emulator)

## Tooling Split

-   **`gcloud` (Control Plane & DDL):** Use for instances, clusters, app profiles,
    backups, IAM, and table/schema management (creating, updating, and deleting
    tables and column families).
-   **`cbt` (Data Plane):** Use for reading, writing, and inspecting data.

## Control Plane (gcloud)

### Instance and Cluster Management

```bash
# Create instance with a single cluster
gcloud bigtable instances create ${BIGTABLE_INSTANCE} \
    --project=${BIGTABLE_PROJECT} \
    --display-name="{display_name}" \
    --cluster-config=id=${BIGTABLE_CLUSTER},zone={zone},nodes={num_nodes}

# Add a cluster to an existing instance
gcloud bigtable clusters create ${BIGTABLE_CLUSTER} \
    --instance=${BIGTABLE_INSTANCE} \
    --zone={zone} \
    --nodes={num_nodes}

# Delete instance
gcloud bigtable instances delete ${BIGTABLE_INSTANCE} --project=${BIGTABLE_PROJECT} --quiet
```

### Table and Schema Management

```bash
# Create table with a column family
gcloud bigtable instances tables create {table_name} \
    --instance=${BIGTABLE_INSTANCE} \
    --column-families={family_name}

# Create table with multiple column families and GC policies
gcloud bigtable instances tables create {table_name} \
    --instance=${BIGTABLE_INSTANCE} \
    --column-families="family1:maxage=10d,family2:maxversions=5"
```

### Backup and Restore

```bash
# Create a backup
gcloud bigtable backups create {backup_id} \
    --instance=${BIGTABLE_INSTANCE} \
    --cluster=${BIGTABLE_CLUSTER} \
    --table={table_id} \
    --retention-period=7d

# Restore a table from backup
gcloud bigtable instances tables restore \
    --source=projects/{project_id_source}/instances/{instance_id_source}/clusters/${BIGTABLE_CLUSTER}/backups/{backup_id} \
    --destination={new_table_id} \
    --destination-instance={instance_id_destination} \
    --project={project_id_destination} \
    --async
```

## Data Plane (cbt)

### Table and Schema Operations

```bash
# Create/Delete table
cbt createtable {table_name}
cbt deletetable {table_name}

# List tables and families
cbt ls
cbt ls {table_name}

# Create/Delete column family
cbt createfamily {table_name} {family_name}
cbt setgcpolicy {table_name} {family_name} "maxversions=1"
cbt deletefamily {table_name} {family_name}
```

## Observability and Performance

### Hotspotting Diagnosis

When performance degrades or a "hotspot" is suspected:

1.  **Key Visualizer:** Direct the user to the Google Cloud Console. Key
    Visualizer provides a heatmap of access patterns across row keys.
2.  **List Hot Tablets (gcloud):** Identify specific tablets with high CPU
    usage.

    ```bash
    gcloud bigtable hot-tablets list ${BIGTABLE_CLUSTER} --instance=${BIGTABLE_INSTANCE}
    ```

## Local Development (Emulator)

Start the Bigtable emulator for testing:

```bash
gcloud beta emulators bigtable start --host-port=localhost:8086
```

To point `cbt` or client libraries to the emulator:

```bash
export BIGTABLE_EMULATOR_HOST=localhost:8086
```

> [!NOTE]
> Bigtable emulator doesn't support Bigtable GoogleSQL yet.
