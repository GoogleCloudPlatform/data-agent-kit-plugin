#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Hermetic unit tests for spark_env_inspector."""

import contextlib
import io
import json
import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
)
# pylint: disable=g-import-not-at-top
import spark_env_inspector


class _FakeGcloud:
  """Deterministic fake command runner keyed by gcloud subcommand prefix."""

  def __init__(self, handlers):
    self._handlers = handlers
    self.calls = []

  def __call__(self, args):
    self.calls.append(list(args))
    cmd_str = " ".join(args)
    for prefix, response in self._handlers.items():
      if cmd_str.startswith(prefix):
        if callable(response):
          return response(args)
        code, payload, stderr = response
        if isinstance(payload, (dict, list)):
          stdout = json.dumps(payload)
        else:
          stdout = str(payload)
        return code, stdout, stderr
    return 1, "", f"ERROR: Unhandled fake gcloud command: {cmd_str}"


def _run_cli(argv, runner):
  out_buf = io.StringIO()
  err_buf = io.StringIO()
  with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
    code = spark_env_inspector.main(argv, runner=runner)
  return code, out_buf.getvalue(), err_buf.getvalue()


class SparkEnvInspectorIdentityTest(unittest.TestCase):

  def test_batch_identity_cmek_iam_and_redaction(self):
    az_key = "spark.hadoop.fs.azure.account.key.acct.blob.core.windows.net"
    runner_member = (
        "serviceAccount:spark-runner@my-gcp-project.iam.gserviceaccount.com"
    )
    batch_payload = {
        "state": "FAILED",
        "stateMessage": "Job failed with exit code 1",
        "runtimeConfig": {
            "version": "3.0",
            "properties": {
                "spark.sql.catalog.lake": (
                    "org.apache.iceberg.spark.SparkCatalog"
                ),
                "spark.sql.catalog.lake.warehouse": (
                    "gs://my-gcp-project-warehouse/iceberg"
                ),
                "spark.sql.catalog.lake.header.X-Iceberg-Access-Delegation": (
                    "vended-credentials"
                ),
                "spark.sql.catalog.lake.credential": "cid:OAuthSecret456",
                "spark.sql.catalog.lake.header.Authorization": (
                    "Bearer ya29.SecretBearerToken"
                ),
                "spark.ssl.keyStorePassphrase": "KeyStorePassphrase88",
                "spark.datasource.jdbc.url": (
                    "jdbc:postgresql://10.0.0.5:5432/prod?"
                    "user=etl&password=InlineUrlPass55&sslmode=require"
                ),
                "spark.datasource.jdbc.password": "CleartextSecret123!",
                "spark.hadoop.fs.s3a.secret.key": "AwsSecretKey999",
                az_key: "AzureStorageKey777",
            },
        },
        "environmentConfig": {
            "executionConfig": {
                "serviceAccount": (
                    "spark-runner@my-gcp-project.iam.gserviceaccount.com"
                ),
                "kmsKey": (
                    "projects/my-gcp-project/locations/us-central1/"
                    "keyRings/dp-ring/cryptoKeys/dp-cmek"
                ),
                "stagingBucket": "my-gcp-project-staging",
            }
        },
    }
    iam_payload = {
        "bindings": [
            {
                "role": "roles/dataproc.worker",
                "members": [runner_member],
            },
            {
                "role": "roles/bigquery.dataViewer",
                "members": [runner_member],
                "condition": {"title": "analytics_only"},
            },
        ]
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-lakehouse": (0, batch_payload, ""),
        "projects get-iam-policy my-gcp-project": (0, iam_payload, ""),
    })

    code, stdout, stderr = _run_cli(
        [
            "--project=my-gcp-project",
            "--region=us-central1",
            "--batch_id=batch-lakehouse",
            "--action=identity",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0, msg=stderr)
    report = json.loads(stdout)
    self.assertEqual(
        report["effective_service_account"],
        "spark-runner@my-gcp-project.iam.gserviceaccount.com",
    )
    self.assertFalse(report["default_service_account_inferred"])
    self.assertIn("dp-cmek", report["kms_key"])
    self.assertEqual(
        report["project_iam_roles"],
        [
            "roles/bigquery.dataViewer (condition: analytics_only)",
            "roles/dataproc.worker",
        ],
    )
    # Safe metadata keys remain readable; raw secrets are redacted.
    auth_props = report["auth_related_properties"]
    self.assertEqual(
        auth_props["spark.sql.catalog.lake.header.X-Iceberg-Access-Delegation"],
        "vended-credentials",
    )
    self.assertEqual(
        auth_props["spark.hadoop.fs.s3a.secret.key"], "<REDACTED>"
    )
    self.assertEqual(
        auth_props["spark.sql.catalog.lake.credential"], "<REDACTED>"
    )
    self.assertEqual(
        auth_props["spark.sql.catalog.lake.header.Authorization"],
        "<REDACTED>",
    )
    self.assertEqual(
        auth_props["spark.ssl.keyStorePassphrase"], "<REDACTED>"
    )
    self.assertNotIn("CleartextSecret123!", stdout)
    self.assertNotIn("OAuthSecret456", stdout)
    self.assertNotIn("SecretBearerToken", stdout)
    self.assertNotIn("KeyStorePassphrase88", stdout)
    self.assertNotIn("InlineUrlPass55", stdout)
    self.assertNotIn("AwsSecretKey999", stdout)
    self.assertNotIn("AzureStorageKey777", stdout)

  def test_serverless_30_defaults_to_end_user_credentials_when_sa_unset(self):
    batch_payload = {
        "state": "FAILED",
        "runtimeConfig": {"version": "3.0"},
        "environmentConfig": {"executionConfig": {}},
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-rt30-euc": (0, batch_payload, ""),
    })
    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-rt30-euc",
            "--action=identity",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    report = json.loads(stdout)
    self.assertEqual(report["effective_service_account"], "")
    self.assertFalse(report["default_service_account_inferred"])
    self.assertEqual(
        report["user_workload_authentication_type"], "END_USER_CREDENTIALS"
    )

  def test_batch_infers_default_compute_sa_when_unset(self):
    batch_payload = {
        "state": "FAILED",
        "runtimeConfig": {"version": "2.2"},
        "environmentConfig": {"executionConfig": {}},
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-default-sa": (0, batch_payload, ""),
        "projects describe my-gcp-project": (
            0,
            {"projectNumber": "123456789012"},
            "",
        ),
        "projects get-iam-policy my-gcp-project": (
            1,
            "",
            "ERROR: (gcloud.projects.get-iam-policy) PERMISSION_DENIED: 403",
        ),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-default-sa",
            "--action=identity",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    report = json.loads(stdout)
    self.assertEqual(
        report["effective_service_account"],
        "123456789012-compute@developer.gserviceaccount.com",
    )
    self.assertTrue(report["default_service_account_inferred"])
    self.assertEqual(len(report["warnings"]), 1)
    self.assertIn("PERMISSION_DENIED", report["warnings"][0])

  def test_cluster_job_identity_scopes_and_secret_manager_versions(self):
    job_payload = {
        "placement": {"clusterName": "etl-std-cluster"},
        "status": {"state": "ERROR", "details": "Secret version is DESTROYED"},
        "pysparkJob": {"mainPythonFileUri": "gs://bkt/ingest_pg.py"},
    }
    cluster_payload = {
        "config": {
            "configBucket": "cluster-cfg-bkt",
            "tempBucket": "cluster-tmp-bkt",
            "softwareConfig": {"imageVersion": "2.2.10-debian12"},
            "gceClusterConfig": {
                "serviceAccount": (
                    "vm-worker@my-gcp-project.iam.gserviceaccount.com"
                ),
                "serviceAccountScopes": [
                    "https://www.googleapis.com/auth/devstorage.read_only"
                ],
            },
        }
    }
    secret_versions = [
        {
            "name": "projects/sec-proj/secrets/pg-pass/versions/2",
            "state": "ENABLED",
            "createTime": "2026-03-02T00:00:00Z",
        },
        {
            "name": "projects/sec-proj/secrets/pg-pass/versions/1",
            "state": "DESTROYED",
            "createTime": "2026-03-01T00:00:00Z",
        },
    ]
    other_member = (
        "serviceAccount:other-sa@my-gcp-project.iam.gserviceaccount.com"
    )
    secret_iam = {
        "bindings": [
            {
                "role": "roles/secretmanager.secretAccessor",
                "members": [other_member],
            }
        ]
    }
    runner = _FakeGcloud({
        "dataproc jobs describe job-jdbc-cluster": (0, job_payload, ""),
        "dataproc clusters describe etl-std-cluster": (0, cluster_payload, ""),
        "projects get-iam-policy my-gcp-project": (0, {"bindings": []}, ""),
        "secrets versions list pg-pass": (0, secret_versions, ""),
        "secrets get-iam-policy pg-pass": (0, secret_iam, ""),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--job_id=job-jdbc-cluster",
            "--action=identity",
            "--secret_id=projects/sec-proj/secrets/pg-pass/versions/1",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    report = json.loads(stdout)
    self.assertEqual(
        report["service_account_scopes"],
        ["https://www.googleapis.com/auth/devstorage.read_only"],
    )
    sec = report["secret_inspection"]
    self.assertEqual(sec["secret_project"], "sec-proj")
    self.assertEqual(sec["secret_id"], "pg-pass")
    self.assertEqual(sec["effective_sa_roles_on_secret"], [])
    states = {v["version"]: v["state"] for v in sec["versions"]}
    self.assertEqual(states, {"1": "DESTROYED", "2": "ENABLED"})
    # Verify secret payload is never accessed.
    for call_args in runner.calls:
      self.assertNotIn("access", call_args)

  def test_deleted_cluster_degrades_with_warning(self):
    job_payload = {
        "placement": {"clusterName": "ephemeral-deleted-cluster"},
        "status": {"state": "ERROR"},
    }
    not_found_err = (
        "ERROR: (gcloud.dataproc.clusters.describe) NOT_FOUND: Cluster not"
        " found"
    )
    runner = _FakeGcloud({
        "dataproc jobs describe job-orphan": (0, job_payload, ""),
        "dataproc clusters describe ephemeral-deleted-cluster": (
            1,
            "",
            not_found_err,
        ),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--job_id=job-orphan",
            "--action=identity",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    self.assertIn("ephemeral-deleted-cluster", stdout)
    self.assertIn("Warnings (Partial Visibility)", stdout)
    self.assertIn("NOT_FOUND", stdout)


class SparkEnvInspectorNetworkTest(unittest.TestCase):

  def test_serverless_no_pga_no_nat_and_tiny_cidr(self):
    batch_payload = {
        "state": "FAILED",
        "stateMessage": "Subnetwork IP space exhausted",
        "runtimeConfig": {"version": "2.2"},
        "environmentConfig": {
            "executionConfig": {
                "subnetworkUri": (
                    "projects/shared-host/regions/us-central1/"
                    "subnetworks/subnet-tiny28"
                ),
                "networkTags": ["spark-egress"],
            }
        },
    }
    subnet_payload = {
        "name": "subnet-tiny28",
        "network": (
            "https://www.googleapis.com/compute/v1/projects/shared-host/"
            "global/networks/analytics-vpc"
        ),
        "ipCidrRange": "10.20.30.0/28",
        "privateIpGoogleAccess": False,
        "purpose": "PRIVATE",
        "stackType": "IPV4_ONLY",
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-shared-vpc": (0, batch_payload, ""),
        "compute networks subnets describe subnet-tiny28": (
            0,
            subnet_payload,
            "",
        ),
        "compute routers list": (0, [], ""),
        "compute firewall-rules list": (0, [], ""),
        "dns managed-zones list": (0, [], ""),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=service-proj",
            "--region=us-central1",
            "--batch_id=batch-shared-vpc",
            "--action=network",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    report = json.loads(stdout)
    self.assertEqual(report["effective_host_project"], "shared-host")
    self.assertEqual(report["effective_network"], "analytics-vpc")
    self.assertTrue(report["internal_ip_only"])
    self.assertFalse(report["subnet"]["private_ip_google_access"])
    self.assertEqual(report["subnet"]["usable_hosts_estimate"], 12)
    self.assertEqual(report["cloud_nats"], [])

  def test_cluster_firewall_port_match_and_unbound_private_dns(self):
    job_payload = {
        "placement": {"clusterName": "pg-ingest-cluster"},
        "status": {"state": "ERROR"},
    }
    cluster_payload = {
        "config": {
            "softwareConfig": {"imageVersion": "2.2-debian12"},
            "gceClusterConfig": {
                "subnetworkUri": "regions/us-central1/subnetworks/subnet-main",
                "internalIpOnly": True,
                "tags": ["dataproc-vm"],
            },
        }
    }
    subnet_payload = {
        "name": "subnet-main",
        "network": "projects/my-gcp-project/global/networks/ingest-vpc",
        "ipCidrRange": "10.10.0.0/20",
        "privateIpGoogleAccess": True,
    }
    routers_payload = [
        {
            "name": "ingest-router",
            "network": "projects/my-gcp-project/global/networks/ingest-vpc",
        }
    ]
    nats_payload = [
        {
            "name": "ingest-nat",
            "sourceSubnetworkIpRangesToNat": "LIST_OF_SUBNETWORKS",
            "subnetworks": [{"name": "regions/us-central1/subnetworks/other"}],
        },
        {
            "name": "private-inter-vpc-nat",
            "type": "PRIVATE",
            "sourceSubnetworkIpRangesToNat": (
                "ALL_SUBNETWORKS_ALL_IP_RANGES"
            ),
        },
        {
            "name": "secondary-only-nat",
            "sourceSubnetworkIpRangesToNat": "LIST_OF_SUBNETWORKS",
            "subnetworks": [{
                "name": "regions/us-central1/subnetworks/subnet-main",
                "sourceIpRangesToNat": ["LIST_OF_SECONDARY_IP_RANGES"],
            }],
        },
    ]
    firewalls_payload = [
        {
            "name": "deny-postgres-egress",
            "network": "projects/my-gcp-project/global/networks/ingest-vpc",
            "direction": "EGRESS",
            "priority": 900,
            "destinationRanges": ["10.50.0.0/16"],
            "targetTags": ["dataproc-vm"],
            "denied": [{"IPProtocol": "tcp", "ports": ["5400-5500"]}],
        },
        {
            "name": "other-sa-scoped-egress",
            "network": "projects/my-gcp-project/global/networks/ingest-vpc",
            "direction": "EGRESS",
            "priority": 950,
            "destinationRanges": ["10.50.0.0/16"],
            "targetServiceAccounts": [
                "unrelated@my-gcp-project.iam.gserviceaccount.com"
            ],
            "denied": [{"IPProtocol": "tcp", "ports": ["5432"]}],
        },
        {
            "name": "disabled-rule",
            "disabled": True,
            "network": "projects/my-gcp-project/global/networks/ingest-vpc",
            "direction": "EGRESS",
            "priority": 100,
            "denied": [{"IPProtocol": "all"}],
        },
    ]
    dns_payload = [
        {
            "name": "corp-db-private-zone",
            "dnsName": "db.internal.example.",
            "visibility": "private",
            "privateVisibilityConfig": {
                "networks": [
                    {
                        "networkUrl": (
                            "https://www.googleapis.com/compute/v1/projects/"
                            "my-gcp-project/global/networks/isolated-vpc"
                        )
                    }
                ]
            },
        }
    ]
    runner = _FakeGcloud({
        "dataproc jobs describe job-private-db": (0, job_payload, ""),
        "dataproc clusters describe pg-ingest-cluster": (
            0,
            cluster_payload,
            "",
        ),
        "compute networks subnets describe subnet-main": (
            0,
            subnet_payload,
            "",
        ),
        "compute routers list": (0, routers_payload, ""),
        "compute routers nats list": (0, nats_payload, ""),
        "compute firewall-rules list": (0, firewalls_payload, ""),
        "dns managed-zones list": (0, dns_payload, ""),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--job_id=job-private-db",
            "--action=network",
            "--target_port=5432",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    report = json.loads(stdout)
    self.assertTrue(
        all(not n["covers_workload_subnet"] for n in report["cloud_nats"])
    )
    self.assertEqual(len(report["firewall_rules"]), 2)
    fw = report["firewall_rules"][0]
    self.assertEqual(fw["name"], "deny-postgres-egress")
    self.assertEqual(fw["action"], "DENY")
    self.assertTrue(fw["applies_to_workload_tags"])
    self.assertTrue(fw["matches_target_port"])
    other_fw = report["firewall_rules"][1]
    self.assertEqual(other_fw["name"], "other-sa-scoped-egress")
    self.assertFalse(other_fw["applies_to_workload_tags"])
    zone = report["private_dns_zones"][0]
    self.assertEqual(zone["dns_name"], "db.internal.example.")
    self.assertFalse(zone["bound_to_workload_network"])

  def test_network_partial_403_tolerance(self):
    batch_payload = {
        "state": "FAILED",
        "runtimeConfig": {"version": "2.2"},
        "environmentConfig": {
            "executionConfig": {
                "subnetworkUri": "regions/us-central1/subnetworks/sub-1"
            }
        },
    }
    subnet_payload = {
        "name": "sub-1",
        "network": "projects/my-gcp-project/global/networks/vpc-1",
        "ipCidrRange": "10.0.0.0/24",
        "privateIpGoogleAccess": False,
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-403": (0, batch_payload, ""),
        "compute networks subnets describe sub-1": (0, subnet_payload, ""),
        "compute routers list": (
            1,
            "",
            "ERROR: PERMISSION_DENIED: compute.routers.list",
        ),
        "compute firewall-rules list": (
            1,
            "",
            "ERROR: PERMISSION_DENIED: compute.firewalls.list",
        ),
        "dns managed-zones list": (
            1,
            "",
            "ERROR: PERMISSION_DENIED: dns.managedZones.list",
        ),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-403",
            "--action=network",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    report = json.loads(stdout)
    self.assertFalse(report["subnet"]["private_ip_google_access"])
    self.assertEqual(len(report["warnings"]), 3)


class SparkEnvInspectorClasspathTest(unittest.TestCase):

  def test_runtime_30_scala_abi_mismatch_and_jar_entrypoint(self):
    bq_jar = (
        "gs://spark-lib/bigquery/"
        "spark-bigquery-with-dependencies_2.12-0.41.0.jar"
    )
    batch_payload = {
        "state": "FAILED",
        "runtimeConfig": {
            "version": "3.0",
            "properties": {
                "spark.jars.packages": (
                    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1"
                ),
                "spark.driver.userClassPathFirst": "true",
                "spark.sql.ansi.enabled": "true",
                "spark.sql.adaptive.enabled": "false",
                "spark.sql.files.maxPartitionBytes": "1024",
                "spark.driver.extraJavaOptions": (
                    "-Djavax.net.ssl.trustStorePassword=TrustPass77 -Xmx4g"
                ),
            },
        },
        "sparkBatch": {
            "mainJarFileUri": "gs://my-gcp-project-code/spanner-ingest.jar",
            "mainClass": "com.example.ingestion.SpannerIngestApp",
            "jarFileUris": [
                bq_jar,
                "gs://my-gcp-project-code/postgresql-42.7.3.jar",
            ],
            "args": [
                "--source=spanner",
                "--use-secret-manager",
                "--db-password=PlainPassword99",
                "--api-token",
                "SecretTokenValue",
                "--secret_id",
                "projects/sec-proj/secrets/pg-pass",
                "--jdbc-url=jdbc:postgresql://db/p?user=u&password=UrlPw88",
                "https://svc:UriSecret66@api.internal/feed",
            ],
        },
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-scala-abi": (0, batch_payload, ""),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-scala-abi",
            "--action=classpath",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    report = json.loads(stdout)
    self.assertEqual(report["runtime_spark_version"], "4.0")
    self.assertEqual(report["runtime_scala_binary_version"], "2.13")
    self.assertEqual(
        report["main_jar_file_uri"],
        "gs://my-gcp-project-code/spanner-ingest.jar",
    )
    self.assertEqual(
        report["main_class"], "com.example.ingestion.SpannerIngestApp"
    )
    by_artifact = {
        item["artifact"]: item["scala_binary_version"]
        for item in report["classified_jars"]
    }
    self.assertEqual(by_artifact[bq_jar], "2.12")
    self.assertEqual(
        by_artifact["org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1"],
        "2.12",
    )
    self.assertIsNone(
        by_artifact["gs://my-gcp-project-code/postgresql-42.7.3.jar"]
    )
    self.assertEqual(
        report["args"],
        [
            "--source=spanner",
            "--use-secret-manager",
            "--db-password=<REDACTED>",
            "--api-token",
            "<REDACTED>",
            "--secret_id",
            "projects/sec-proj/secrets/pg-pass",
            "--jdbc-url=jdbc:postgresql://db/p?user=u&password=<REDACTED>",
            "https://svc:<REDACTED>@api.internal/feed",
        ],
    )
    self.assertNotIn("PlainPassword99", stdout)
    self.assertNotIn("SecretTokenValue", stdout)
    self.assertNotIn("TrustPass77", stdout)
    self.assertNotIn("UrlPw88", stdout)
    self.assertNotIn("UriSecret66", stdout)
    cp_props = report["classpath_and_catalog_properties"]
    self.assertEqual(cp_props["spark.sql.adaptive.enabled"], "false")
    self.assertEqual(cp_props["spark.sql.files.maxPartitionBytes"], "1024")
    self.assertEqual(
        cp_props["spark.driver.extraJavaOptions"],
        "-Djavax.net.ssl.trustStorePassword=<REDACTED> -Xmx4g",
    )

  def test_cluster_spark_prefix_properties_and_runtime_matrix(self):
    job_payload = {
        "placement": {"clusterName": "std-cluster-22"},
        "status": {"state": "ERROR"},
        "pysparkJob": {
            "mainPythonFileUri": "gs://bkt/job.py",
            "properties": {"spark.files": "gs://bkt/override-ca.pem"},
        },
    }
    cluster_22 = {
        "config": {
            "softwareConfig": {
                "imageVersion": "2.2.15-debian12",
                "optionalComponents": ["ICEBERG"],
                "properties": {
                    "spark:spark.jars": "gs://bkt/custom_2.12-1.0.jar",
                    "spark:spark.files": "gs://bkt/cluster-ca.pem",
                },
            }
        }
    }
    runner_22 = _FakeGcloud({
        "dataproc jobs describe job-c22": (0, job_payload, ""),
        "dataproc clusters describe std-cluster-22": (0, cluster_22, ""),
    })
    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--job_id=job-c22",
            "--action=classpath",
            "--format=json",
        ],
        runner_22,
    )
    self.assertEqual(code, 0)
    rep_22 = json.loads(stdout)
    # GCE Cluster Image 2.2 runs Spark 3.5 on Scala 2.12.
    self.assertEqual(rep_22["runtime_spark_version"], "3.5")
    self.assertEqual(rep_22["runtime_scala_binary_version"], "2.12")
    self.assertEqual(rep_22["jar_file_uris"], ["gs://bkt/custom_2.12-1.0.jar"])
    self.assertEqual(rep_22["file_uris"], ["gs://bkt/override-ca.pem"])

    # GCE Cluster Image 3.0 runs Spark 4.1 on Scala 2.13.
    cluster_30 = {
        "config": {"softwareConfig": {"imageVersion": "3.0.2-debian12"}}
    }
    runner_30 = _FakeGcloud({
        "dataproc jobs describe job-c30": (
            0,
            {"placement": {"clusterName": "c30"}, "status": {"state": "DONE"}},
            "",
        ),
        "dataproc clusters describe c30": (0, cluster_30, ""),
    })
    code30, stdout30, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--job_id=job-c30",
            "--action=classpath",
            "--format=json",
        ],
        runner_30,
    )
    self.assertEqual(code30, 0)
    rep_30 = json.loads(stdout30)
    self.assertEqual(rep_30["runtime_spark_version"], "4.1")
    self.assertEqual(rep_30["runtime_scala_binary_version"], "2.13")

  def test_interactive_session_and_markdown_rendering(self):
    session_payload = {
        "state": "ACTIVE",
        "runtimeConfig": {
            "version": "2.2",
            "properties": {
                "spark.sql.catalog.biglake_cat": (
                    "org.apache.iceberg.spark.SparkCatalog"
                ),
                "spark.datasource.bigquery.viewsEnabled": "false",
            },
        },
        "jupyterSession": {"displayName": "Interactive Notebook"},
    }
    runner = _FakeGcloud({
        "beta dataproc sessions describe session-interactive": (
            0,
            session_payload,
            "",
        ),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--location=us-east1",
            "--session_id=session-interactive",
            "--action=classpath",
            "--format=markdown",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    self.assertIn("runtime_spark_version: `3.5`", stdout)
    self.assertIn("runtime_scala_binary_version: `2.13`", stdout)
    self.assertIn("spark.datasource.bigquery.viewsEnabled", stdout)
    # Verify `--location` was passed to `gcloud beta dataproc sessions`.
    self.assertIn("--location=us-east1", runner.calls[0])

  def test_interactive_session_falls_back_to_ga_when_beta_missing(self):
    session_payload = {
        "state": "ACTIVE",
        "runtimeConfig": {"version": "3.0"},
        "jupyterSession": {"displayName": "GA Session"},
    }
    runner = _FakeGcloud({
        "beta dataproc sessions describe session-ga": (
            1,
            "",
            "ERROR: (gcloud) Invalid choice: 'beta'.",
        ),
        "dataproc sessions describe session-ga": (0, session_payload, ""),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--location=us-central1",
            "--session_id=session-ga",
            "--action=classpath",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    report = json.loads(stdout)
    self.assertEqual(report["runtime_spark_version"], "4.0")
    self.assertEqual(report["warnings"], [])

  def test_primary_workload_not_found_returns_nonzero(self):
    batch_not_found = (
        "ERROR: (gcloud.dataproc.batches.describe) NOT_FOUND: Batch not found"
    )
    runner = _FakeGcloud({
        "dataproc batches describe missing-batch": (
            1,
            "",
            batch_not_found,
        ),
    })
    code, _, stderr = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=missing-batch",
            "--action=identity",
        ],
        runner,
    )
    self.assertEqual(code, 1)
    self.assertIn("NOT_FOUND", stderr)

  def test_missing_project_returns_nonzero(self):
    runner = _FakeGcloud({
        "config get-value project": (0, "(unset)\n", ""),
    })
    code, _, stderr = _run_cli(
        ["--batch_id=b1", "--action=identity"],
        runner,
    )
    self.assertEqual(code, 1)
    self.assertIn("No project given", stderr)


if __name__ == "__main__":
  unittest.main()
