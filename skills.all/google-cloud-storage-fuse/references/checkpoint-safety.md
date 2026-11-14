# Checkpoint & Write Safety

Verdicts on write patterns through a gcsfuse mount — above all the standard
checkpoint publish pattern (write `ckpt.tmp/`, rename to the final name) that
must survive preemption.

## Verdict table (lead with this)

Write pattern                                        | Flat-namespace bucket                                                                                            | HNS bucket
:--------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------- | :---------
Rename a **file** to finalize                        | Safe — atomic MoveObject since v3.2.0                                                                            | Safe — atomic since v3.1.0
Rename a **directory** to finalize                   | **Fails by default** (`rename-dir-limit: 0`); raising the limit makes it a **non-atomic** per-object copy+delete | Safe — atomic `RenameFolder`, metadata-only
`fsync()` for durability                             | **Not durable** under streaming writes (the default for new files) — rely on `close()`                           | Same — rely on `close()`
Concurrent writers, same object                      | First to close wins; later writers get `ESTALE`. No file locking exists.                                         | Same
Kernel list cache (`kernel-list-cache-ttl-secs: -1`) | **Dangerous** on mutable mounts (directory ghosting, missing files, `rmdir` failures)                            | Same — keep list cache off or low TTL; `-1` is strictly for read-only mounts

So the temp-then-rename pattern is **safe if and only if** the bucket has
hierarchical namespace (HNS) enabled, or the framework renames individual files
rather than directories. On a flat bucket the directory rename fails outright by
default — and "fixing" it by raising `rename-dir-limit` converts a visible
failure into silent corruption risk: preemption mid-rename leaves a
partially-renamed "final" checkpoint.

**Never** describe file renames as "copy + delete, slow but works" — that is
outdated. Files rename atomically via the MoveObject API since v3.1.0 (HNS) and
v3.2.0 (flat buckets); only *directory* renames on *flat* buckets use the
non-atomic per-object path, and only when force-enabled.

**Never** recommend `fsync()` for checkpoint durability. Under streaming writes
(default since v3.0), `fsync()` does not finalize the object; data is guaranteed
on Cloud Storage only after `close()`. This is documented in the gcsfuse GitHub
semantics doc, not on cloud.google.com — cite
[semantics.md](https://github.com/GoogleCloudPlatform/gcsfuse/blob/master/docs/semantics.md)
when the user asks for a source.

**Never** enable `kernel-list-cache-ttl-secs: -1` on mutable or checkpointing
mounts. Client-side kernel list caching does not invalidate when files are added
or deleted during training runs, causing phantom files, missing checkpoint
shards, and `rmdir`/`unlink` errors across distributed workers. `-1` is strictly
for read-only training and serving mounts.

**Never** present `rename-dir-limit` as the fix without stating the
non-atomicity. It is a fallback with a corruption window, not a remedy.

## Diagnosis inputs

Collect before giving a verdict:

```bash
# Namespace type - the deciding signal. Prints "True" for HNS buckets;
# empty output means flat namespace. --raw is required: without it the
# describe output omits the hierarchical namespace field entirely.
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-fuse)" \
gcloud storage buckets describe gs://BUCKET --raw --format="value(hierarchicalNamespace.enabled)"
```

Also determine from the user or the mount config: does the framework rename a
directory or individual files (Orbax and `torch.distributed.checkpoint` finalize
by renaming a checkpoint directory; a plain `torch.save` to a temp name renames
a single file); how many shard writers run concurrently per step; the effective
`write: global-max-blocks` and `file-system: rename-dir-limit`.

## Durability and finalization semantics

-   Objects are visible to readers only after finalization. Under streaming
    writes (default since v3.0, sequential writes to new files), finalization
    happens at `close()` — not at `fsync()`.
-   A read during write, a downward truncate, or a rename during write finalizes
    the object early, and subsequent writes to that handle fall back to staged
    writes.
-   Staged writes (the fallback path: editing existing files, out-of-order
    writes, block-budget exhaustion) buffer the whole file in `file-system:
    temp-dir` (default `/tmp`) and upload on close/flush — an undersized temp
    dir breaks large staged writes.

## Concurrency: first writer wins

There is no file locking (`flock`/`fcntl` are not honored across mounts). When
two mounts write the same object, the first flush/close wins by generation
precondition; the loser's `close()` fails with `ESTALE` (stale file handle).
Design for **one writer per object** — e.g. one shard writer per checkpoint
shard file. `ESTALE` in training logs almost always means two workers wrote the
same path.

## Memory budget for concurrent shard writers

Streaming writes hold one 32 MiB block per actively-written file, capped
globally by `write: global-max-blocks` — default **4** on ordinary machines (128
MiB total; A2/A3/A4-series autoconfigure to 1600). Each streaming file consumes
~96 MiB RAM during upload. When the block budget is exhausted, additional
concurrent writers degrade to staged writes — the only signal is a trace-level
log line, invisible at the default `info` severity, so it looks like an
unexplained slowdown. With N concurrent shard writers, set `write:
global-max-blocks` ≥ N (e.g. `global-max-blocks: 64` for 16 shard writers with
headroom).

## Remediation

**Recommended: move checkpoints to an HNS bucket** — directory renames become
atomic metadata-only `RenameFolder` operations (executed as long-running
operations: reads and lists work during the rename, writes to the affected
folders are blocked until it completes), which is what makes temp-then-rename
safe. HNS buckets also start with up to 8× the initial QPS of flat buckets
(40,000 initial object reads/s and 8,000 writes/s vs. 5,000 and 1,000). HNS can
only be chosen at bucket creation — existing flat buckets cannot be converted,
so plan a new bucket + data copy. Uniform bucket-level access is required for
HNS buckets.

```bash
# Create the HNS checkpoint bucket (--uniform-bucket-level-access is required)
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-fuse)" \
gcloud storage buckets create gs://CKPT_BUCKET --location=LOCATION \
  --uniform-bucket-level-access --enable-hierarchical-namespace

# Copy existing checkpoints if migrating
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-fuse)" \
gcloud storage cp -r gs://OLD_BUCKET/checkpoints gs://CKPT_BUCKET/
```

Mount tuned for checkpointing:

```bash
# Compute Engine / self-managed (profile requires gcsfuse ≥ v3.4.0)
gcsfuse --profile=aiml-checkpointing CKPT_BUCKET /mnt/ckpt
```

On GKE use the `gcsfusecsi-checkpointing` StorageClass (GKE ≥
1.35.1-gke.1616000) — see [GKE Training Deployment](gke-training-deployment.md)
for the PV/PVC pattern; profiles cannot be passed as raw mount options on GKE.

The `aiml-checkpointing` profile sets `implicit-dirs`, infinite metadata TTL and
unlimited stat cache (`ttl-secs: -1`, `stat-cache-max-size-mb: -1`,
`negative-ttl-secs: 0`), `file-cache: cache-file-for-range-read: true` (for
restore-time range reads), and `file-system: rename-dir-limit: 200000`. Note the
rename-dir-limit entry exists for flat-bucket compatibility; on an HNS bucket
directory renames are atomic and need no limit. The profile does **not** enable
the file cache (enable it explicitly if restores should be served from local
media), and keeps the kernel list cache off (`kernel-list-cache-ttl-secs: 0`)
for write safety. Also state the close-time finalization semantics to the user
whenever recommending this setup: checkpoints are durable when the writer closes
the file, not before.

**Fallback (user cannot migrate to HNS):** raise the directory-rename limit on
the flat bucket, stating the risk explicitly —

```yaml
file-system:
  rename-dir-limit: 200000
```

This makes directory renames *possible* but **non-atomic**: each object is
copied and deleted individually, the operation is O(objects) and expensive, and
preemption mid-rename leaves both directories in an inconsistent state. If the
job runs on preemptible/spot capacity, prefer file-level publish patterns (write
shards to temp *names*, rename each file, then write a final manifest file) —
file renames are atomic even on flat buckets.

## Documentation

-   [Cloud Storage FUSE semantics (GitHub)](https://github.com/GoogleCloudPlatform/gcsfuse/blob/master/docs/semantics.md)
-   [Profile-based configurations](https://cloud.google.com/storage/docs/cloud-storage-fuse/profile-based-configurations)
-   [Config file reference](https://cloud.google.com/storage/docs/cloud-storage-fuse/config-file)
-   [Hierarchical namespace overview](https://cloud.google.com/storage/docs/hns-overview)
-   [GKE profiles for Cloud Storage FUSE](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/gcsfuse-profiles)
