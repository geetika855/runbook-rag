# Explainer: how S3 cross-region replication (CRR) works

## What it is
S3 Cross-Region Replication automatically and asynchronously copies objects
from a source bucket to a destination bucket in a different AWS region. Used
for disaster recovery, lower-latency access in other regions, and compliance
(data must exist in two regions).

## Requirements (all must be true)
1. **Versioning enabled on BOTH buckets** — source and destination. CRR
   replicates versions, so without versioning there is nothing to replicate.
2. An **IAM role** that S3 can assume, with `s3:GetObjectVersion`,
   `s3:ReplicateObject`, `s3:ReplicateDelete`, etc. on the relevant buckets.
3. Replication is configured **on the source bucket**, pointing at the
   destination bucket ARN.

## How it works, step by step
1. You define **replication rules** on the source bucket, each with a filter
   (a prefix like `logs/` and/or object tags) and a destination bucket.
2. When a matching object is **written** to the source, S3 queues a
   replication task. Replication is asynchronous — usually seconds to
   minutes.
3. Each replica carries a `REPLICATION_STATUS`: `PENDING` → `COMPLETED`
   (or `FAILED`). You can read it via `aws s3api head-object`.
4. **Deletes are special:** a delete *marker* is replicated (so the object
   looks deleted in both regions), but deleting object *versions* is not —
   version-level deletes never replicate. This protects the replica from
   accidental purges.
5. **Existing objects are NOT replicated by default.** CRR only catches
   objects written after the rule is created. Backfilling needs S3 Batch
   Replication as a one-time job.

## Setting it up (CLI sketch)
```bash
# 1. Versioning on both buckets
aws s3api put-bucket-versioning --bucket src-bucket \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-versioning --bucket dst-bucket \
  --versioning-configuration Status=Enabled

# 2. Replication config on the source (role must already exist)
aws s3api put-bucket-replication --bucket src-bucket \
  --replication-configuration file://replication.json

# 3. Check status of an object
aws s3api head-object --bucket src-bucket --key path/to/object \
  --query ReplicationStatus
```

## Monitoring
- S3 publishes **replication metrics** (operations pending, failed, latency)
  to CloudWatch — alert on `OperationsFailedReplication`.
- For SLA needs, enable **Replication Time Control (RTC)**: replicates 99.99%
  of objects within 15 minutes, with an SLA-backed guarantee (costs extra).

## Gotchas that bite people
- KMS-encrypted objects need the role granted `kms:Decrypt`/`kms:Encrypt`
  on both keys, or replication silently fails.
- Cross-account replication needs the destination bucket policy to allow the
  source role.
- You pay for it three ways: replication requests, inter-region data
  transfer, and storage in the second region.

## Prevention / follow-up
- After setup, upload a canary object and confirm `COMPLETED` status in the
  destination before calling it done.
- Document which prefixes replicate and which don't — partial replication
  surprises people during DR drills.
