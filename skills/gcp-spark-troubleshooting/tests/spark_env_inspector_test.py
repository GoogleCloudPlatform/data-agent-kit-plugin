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
import subprocess
import sys
import unittest
from unittest import mock

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
                "spark.datasource.bigquery.temporaryGcsBucket": "bq-tmp-bkt",
                "spark.executor.memory": "8g",
                "spark.hadoop.fs.s3a.secret.key": "AwsSecretKey999",
                az_key: "AzureStorageKey777",
            },
        },
        "runtimeInfo": {
            "propertiesInfo": {
                "autotuningProperties": {
                    "spark.executor.memory": {
                        "value": "4g",
                        "annotation": "autotuning",
                    },
                    "spark.sql.warehouse.dir": {
                        "value": "gs://eff-warehouse/iceberg"
                    },
                }
            }
        },
        "creator": "pipeline-owner@example.com",
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
    self.assertEqual(list(report.keys()), sorted(report.keys()))
    self.assertEqual(
        report["effective_service_account"],
        "spark-runner@my-gcp-project.iam.gserviceaccount.com",
    )
    self.assertFalse(report["default_service_account_inferred"])
    self.assertEqual(
        report["user_workload_authentication_type"], "SERVICE_ACCOUNT"
    )
    # The workload runs as its service account, not as the batch creator.
    self.assertEqual(
        report["effective_principal"],
        "serviceAccount:spark-runner@my-gcp-project.iam.gserviceaccount.com",
    )
    self.assertEqual(report["creator"], "pipeline-owner@example.com")
    self.assertIn("dp-cmek", report["kms_key"])
    self.assertEqual(report["staging_bucket"], "my-gcp-project-staging")
    self.assertEqual(report["temp_bucket"], "bq-tmp-bkt")
    self.assertEqual(
        report["project_iam_roles"],
        [
            "roles/bigquery.dataViewer (condition: analytics_only)",
            "roles/dataproc.worker",
        ],
    )
    merged = spark_env_inspector._merged_properties(
        "batch", batch_payload, None
    )
    self.assertEqual(merged["spark.executor.memory"], "8g")
    self.assertEqual(
        merged["spark.sql.warehouse.dir"], "gs://eff-warehouse/iceberg"
    )
    # Safe metadata keys remain readable; raw secrets are redacted.
    auth_props = report["auth_related_properties"]
    self.assertNotIn("spark.executor.memory", auth_props)
    self.assertEqual(
        auth_props["spark.sql.warehouse.dir"], "gs://eff-warehouse/iceberg"
    )
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
        "projects describe my-gcp-project": (
            0,
            {"projectNumber": "999999999999"},
            "",
        ),
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
    self.assertEqual(report["warnings"], [])

  def test_auth_type_unspecified_runtime_40_and_explicit_sa_override(self):
    batch_40 = {
        "state": "FAILED",
        "runtimeConfig": {
            "version": "4.0",
            "properties": {"temporaryGcsBucket": "legacy-tmp-bkt"},
        },
        "environmentConfig": {
            "executionConfig": {
                "authenticationConfig": {
                    "userWorkloadAuthenticationType": (
                        "AUTHENTICATION_TYPE_UNSPECIFIED"
                    )
                }
            }
        },
    }
    batch_30_explicit_sa = {
        "state": "FAILED",
        "runtimeConfig": {"version": "3.0"},
        "environmentConfig": {
            "executionConfig": {
                "authenticationConfig": {
                    "userWorkloadAuthenticationType": "SERVICE_ACCOUNT"
                }
            }
        },
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-rt40-unspec": (0, batch_40, ""),
        "dataproc batches describe batch-rt30-sa-mode": (
            0,
            batch_30_explicit_sa,
            "",
        ),
        "projects describe my-gcp-project": (
            0,
            {"projectNumber": "111222333444"},
            "",
        ),
        "projects get-iam-policy my-gcp-project": (0, {"bindings": []}, ""),
    })

    code_40, out_40, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-rt40-unspec",
            "--action=identity",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code_40, 0)
    rep_40 = json.loads(out_40)
    self.assertEqual(
        rep_40["user_workload_authentication_type"], "END_USER_CREDENTIALS"
    )
    self.assertEqual(rep_40["effective_service_account"], "")
    self.assertEqual(rep_40["temp_bucket"], "legacy-tmp-bkt")

    code_sa, out_sa, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-rt30-sa-mode",
            "--action=identity",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code_sa, 0)
    rep_sa = json.loads(out_sa)
    self.assertEqual(
        rep_sa["user_workload_authentication_type"], "SERVICE_ACCOUNT"
    )
    self.assertEqual(
        rep_sa["effective_service_account"],
        "111222333444-compute@developer.gserviceaccount.com",
    )
    self.assertTrue(rep_sa["default_service_account_inferred"])

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
            "encryptionConfig": {
                "gcePdKmsKeyName": (
                    "projects/my-gcp-project/locations/us-central1/"
                    "keyRings/kr/cryptoKeys/pd-cmek"
                )
            },
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
    worker_member = (
        "serviceAccount:vm-worker@my-gcp-project.iam.gserviceaccount.com"
    )
    secret_iam = {
        "bindings": [
            {
                "role": "roles/secretmanager.secretAccessor",
                "members": [other_member],
            },
            {
                "role": "roles/secretmanager.viewer",
                "members": [worker_member],
            },
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
    self.assertIn("pd-cmek", report["kms_key"])
    sec = report["secret_inspection"]
    self.assertEqual(sec["secret_project"], "sec-proj")
    self.assertEqual(sec["secret_id"], "pg-pass")
    self.assertEqual(
        sec["principal_roles_on_secret"], ["roles/secretmanager.viewer"]
    )
    self.assertEqual(sec["iam_bindings"], secret_iam["bindings"])
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
        "projects describe my-gcp-project": (
            0,
            {"projectNumber": "555666777888"},
            "",
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
    self.assertIn("- effective_service_account: `(unresolved)`", stdout)
    self.assertIn("Warnings (Partial Visibility)", stdout)
    self.assertIn("NOT_FOUND", stdout)

    live_cluster_runner = _FakeGcloud({
        "dataproc jobs describe job-live-default-sa": (
            0,
            {
                "placement": {"clusterName": "live-cluster"},
                "status": {"state": "DONE"},
            },
            "",
        ),
        "dataproc clusters describe live-cluster": (
            0,
            {"config": {"gceClusterConfig": {}}},
            "",
        ),
        "projects describe my-gcp-project": (
            0,
            {"projectNumber": "555666777888"},
            "",
        ),
        "projects get-iam-policy my-gcp-project": (0, {"bindings": []}, ""),
    })
    live_code, live_stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--job_id=job-live-default-sa",
            "--action=identity",
            "--format=json",
        ],
        live_cluster_runner,
    )
    self.assertEqual(live_code, 0)
    live_report = json.loads(live_stdout)
    self.assertEqual(
        live_report["effective_service_account"],
        "555666777888-compute@developer.gserviceaccount.com",
    )
    self.assertTrue(live_report["default_service_account_inferred"])


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
    self.assertFalse(report["default_network_inferred"])
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
                "serviceAccount": (
                    "cluster-sa@my-gcp-project.iam.gserviceaccount.com"
                ),
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
    network_payload = {
        "name": "ingest-vpc",
        "networkFirewallPolicyEnforcementOrder": "AFTER_CLASSIC_FIREWALL",
        "peerings": [{
            "name": "to-analytics",
            "network": "projects/analytics-host/global/networks/analytics-vpc",
            "state": "ACTIVE",
            "stateDetails": "[2026-11-01T00:00:00Z]: Connected.",
            "importCustomRoutes": True,
        }],
    }
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
        "compute networks describe ingest-vpc": (0, network_payload, ""),
        "compute firewall-rules list": (0, firewalls_payload, ""),
        "compute network-firewall-policies get-effective-firewalls": (
            0,
            {"firewallPolicys": [], "firewalls": []},
            "",
        ),
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
    self.assertEqual(report["warnings"], [])
    self.assertTrue(
        all(not n["covers_workload_subnet"] for n in report["cloud_nats"])
    )
    self.assertEqual(
        report["workload_service_account"],
        "cluster-sa@my-gcp-project.iam.gserviceaccount.com",
    )
    self.assertFalse(report["workload_service_account_inferred"])
    self.assertEqual(
        report["vpc_peerings"],
        [{
            "name": "to-analytics",
            "peer_project": "analytics-host",
            "peer_network": "analytics-vpc",
            "state": "ACTIVE",
            "state_details": "[2026-11-01T00:00:00Z]: Connected.",
            "import_custom_routes": True,
            "export_custom_routes": False,
        }],
    )
    self.assertEqual(
        report["firewall_policy_enforcement_order"], "AFTER_CLASSIC_FIREWALL"
    )
    self.assertEqual(report["firewall_policies"], [])
    self.assertEqual(len(report["firewall_rules"]), 2)
    fw = report["firewall_rules"][0]
    self.assertEqual(fw["name"], "deny-postgres-egress")
    self.assertEqual(fw["action"], "DENY")
    self.assertTrue(fw["applies_to_workload"])
    self.assertTrue(fw["matches_target_port"])
    other_fw = report["firewall_rules"][1]
    self.assertEqual(other_fw["name"], "other-sa-scoped-egress")
    self.assertFalse(other_fw["applies_to_workload"])
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
        "projects describe my-gcp-project": (
            1,
            "",
            "ERROR: PERMISSION_DENIED: resourcemanager.projects.get",
        ),
        "compute networks subnets describe sub-1": (0, subnet_payload, ""),
        "compute routers list": (
            1,
            "",
            "ERROR: PERMISSION_DENIED: compute.routers.list",
        ),
        "compute networks describe vpc-1": (
            1,
            "",
            "ERROR: PERMISSION_DENIED: compute.networks.get",
        ),
        "compute firewall-rules list": (
            1,
            "",
            "ERROR: PERMISSION_DENIED: compute.firewalls.list",
        ),
        "compute network-firewall-policies get-effective-firewalls": (
            1,
            "",
            "ERROR: PERMISSION_DENIED: compute.networks.getEffectiveFirewalls",
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
    # The default SA could not be resolved, so SA scoping stays unknown.
    self.assertEqual(report["workload_service_account"], "")
    self.assertEqual(len(report["warnings"]), 6)
    self.assertTrue(
        all("PERMISSION_DENIED" in w for w in report["warnings"]),
        msg=report["warnings"],
    )

  def test_network_uri_modes_deleted_cluster_and_subnet_403_guards(self):
    # 1. networkUri without subnetworkUri; omitted internalIpOnly and PGA flags.
    job_net_only = {
        "placement": {"clusterName": "net-only-cluster"},
        "status": {"state": "DONE"},
    }
    cluster_net_only = {
        "config": {
            "gceClusterConfig": {
                "networkUri": "projects/net-host/global/networks/custom-vpc"
            }
        }
    }
    subnet_minimal = {"ipCidrRange": "10.9.0.0/24"}
    runner_net = _FakeGcloud({
        "dataproc jobs describe job-net-only": (0, job_net_only, ""),
        "dataproc clusters describe net-only-cluster": (
            0,
            cluster_net_only,
            "",
        ),
        "compute networks subnets describe custom-vpc": (0, subnet_minimal, ""),
        "compute routers list": (0, [], ""),
        "compute firewall-rules list": (0, [], ""),
        "dns managed-zones list": (0, [], ""),
    })
    rep_net = spark_env_inspector.inspect_network(
        "service-proj", "us-central1", "job", "job-net-only", runner_net
    )
    self.assertFalse(rep_net["default_network_inferred"])
    self.assertFalse(rep_net["internal_ip_only"])
    self.assertEqual(rep_net["effective_host_project"], "net-host")
    self.assertEqual(rep_net["effective_network"], "custom-vpc")
    self.assertEqual(rep_net["effective_subnetwork"], "custom-vpc")
    self.assertEqual(rep_net["subnet"]["name"], "custom-vpc")
    self.assertFalse(rep_net["subnet"]["private_ip_google_access"])

    # 2. Default network inferred; empty dict / non-list responses tolerated.
    runner_default = _FakeGcloud({
        "dataproc batches describe batch-default-net": (
            0,
            {"state": "DONE", "runtimeConfig": {"version": "2.2"}},
            "",
        ),
        "compute networks subnets describe default": (0, {}, ""),
        "compute routers list": (0, {}, ""),
        "compute firewall-rules list": (0, {}, ""),
        "dns managed-zones list": (0, {}, ""),
    })
    rep_def = spark_env_inspector.inspect_network(
        "my-proj", "us-central1", "batch", "batch-default-net", runner_default
    )
    self.assertTrue(rep_def["default_network_inferred"])
    self.assertEqual(rep_def["effective_network"], "default")
    self.assertEqual(rep_def["effective_subnetwork"], "default")
    self.assertIsNone(rep_def["subnet"])

    # 3. Non-dict truthy JSON from subnets describe leaves subnet None.
    runner_list_sub = _FakeGcloud({
        "dataproc batches describe batch-list-sub": (0, {"state": "DONE"}, ""),
        "compute networks subnets describe default": (0, ["unexpected"], ""),
        "compute routers list": (0, [], ""),
        "compute firewall-rules list": (0, [], ""),
        "dns managed-zones list": (0, [], ""),
    })
    rep_list_sub = spark_env_inspector.inspect_network(
        "my-proj", "us-central1", "batch", "batch-list-sub", runner_list_sub
    )
    self.assertIsNone(rep_list_sub["subnet"])

    # 4. Deleted cluster job skips all VPC queries even if VPC handlers exist.
    runner_del_cluster = _FakeGcloud({
        "dataproc jobs describe job-del-net": (
            0,
            {"placement": {"clusterName": "gone-cluster"}},
            "",
        ),
        "dataproc clusters describe gone-cluster": (
            1,
            "",
            "ERROR: NOT_FOUND: Cluster gone-cluster",
        ),
        "compute networks subnets describe default": (0, subnet_minimal, ""),
        "compute routers list": (0, [{"name": "r1", "network": "default"}], ""),
        "compute firewall-rules list": (
            0,
            [{"name": "fw1", "network": "default", "direction": "EGRESS"}],
            "",
        ),
        "dns managed-zones list": (
            0,
            [{"name": "z1", "visibility": "private"}],
            "",
        ),
    })
    rep_del = spark_env_inspector.inspect_network(
        "my-proj", "us-central1", "job", "job-del-net", runner_del_cluster
    )
    self.assertIsNone(rep_del["subnet"])
    self.assertEqual(rep_del["cloud_nats"], [])
    self.assertEqual(rep_del["firewall_rules"], [])
    self.assertEqual(rep_del["private_dns_zones"], [])
    self.assertEqual(len(rep_del["warnings"]), 1)

    # 5. Subnetwork 403 when networkUri is unset leaves network_name empty and
    # skips router/firewall/DNS matching against an unknown network.
    runner_sub_403 = _FakeGcloud({
        "dataproc batches describe batch-sub-403": (
            0,
            {
                "environmentConfig": {
                    "executionConfig": {
                        "subnetworkUri": (
                            "regions/us-central1/subnetworks/sub-x"
                        ),
                        "serviceAccount": "etl@my-proj.iam.gserviceaccount.com",
                    }
                }
            },
            "",
        ),
        "compute networks subnets describe sub-x": (
            1,
            "",
            "ERROR: PERMISSION_DENIED: subnetworks.get",
        ),
        "compute routers list": (0, [{"name": "r1", "network": ""}], ""),
        "compute firewall-rules list": (
            0,
            [{"name": "fw1", "network": "", "direction": "EGRESS"}],
            "",
        ),
        "dns managed-zones list": (
            0,
            [{"name": "z1", "visibility": "private"}],
            "",
        ),
    })
    rep_sub_403 = spark_env_inspector.inspect_network(
        "my-proj", "us-central1", "batch", "batch-sub-403", runner_sub_403
    )
    self.assertEqual(rep_sub_403["effective_network"], "")
    self.assertIsNone(rep_sub_403["subnet"])
    self.assertEqual(rep_sub_403["cloud_nats"], [])
    self.assertEqual(rep_sub_403["firewall_rules"], [])
    self.assertEqual(rep_sub_403["private_dns_zones"], [])
    self.assertEqual(len(rep_sub_403["warnings"]), 1)

  def test_nat_coverage_firewall_filtering_sorting_and_dns_visibility(self):
    batch_payload = {
        "state": "FAILED",
        "runtimeConfig": {"version": "3.0"},
        "environmentConfig": {
            "executionConfig": {
                "subnetworkUri": "regions/us-central1/subnetworks/subnet-main",
                "serviceAccount": "worker@my-proj.iam.gserviceaccount.com",
            }
        },
    }
    subnet_payload = {
        "name": "subnet-main",
        "network": "projects/my-proj/global/networks/ingest-vpc",
        "ipCidrRange": "10.0.0.0/24",
        "privateIpGoogleAccess": True,
    }
    routers_payload = [
        {
            "name": "other-vpc-router",
            "network": "projects/my-proj/global/networks/other-vpc",
        },
        {
            "name": "",
            "network": "projects/my-proj/global/networks/ingest-vpc",
        },
        {
            "name": "dict-nats-router",
            "network": "projects/my-proj/global/networks/ingest-vpc",
        },
        {
            "name": "ingest-router",
            "network": "projects/my-proj/global/networks/ingest-vpc",
        },
    ]
    nats_payload = [
        {
            "name": "nat-default-ranges",
            "sourceSubnetworkIpRangesToNat": "LIST_OF_SUBNETWORKS",
            "subnetworks": [
                "corrupted-entry",
                {"name": "regions/us-central1/subnetworks/subnet-main"},
            ],
        },
        {
            "name": "nat-all-ip-ranges",
            "sourceSubnetworkIpRangesToNat": "LIST_OF_SUBNETWORKS",
            "subnetworks": [{
                "name": "regions/us-central1/subnetworks/subnet-main",
                "sourceIpRangesToNat": ["ALL_IP_RANGES"],
            }],
        },
        {
            "name": "nat-primary-range",
            "sourceSubnetworkIpRangesToNat": "LIST_OF_SUBNETWORKS",
            "subnetworks": [{
                "name": "regions/us-central1/subnetworks/subnet-main",
                "sourceIpRangesToNat": ["PRIMARY_IP_RANGE"],
            }],
        },
        {
            "name": "nat-all-subnets",
            "sourceSubnetworkIpRangesToNat": "ALL_SUBNETWORKS_ALL_IP_RANGES",
        },
    ]
    firewalls_payload = [
        {
            "name": "other-vpc-fw",
            "network": "projects/my-proj/global/networks/other-vpc",
            "direction": "EGRESS",
            "priority": 100,
            "denied": [{"IPProtocol": "all"}],
        },
        {
            "name": "ingress-allow-mysql",
            "network": "projects/my-proj/global/networks/ingest-vpc",
            "direction": "INGRESS",
            "priority": 200,
            "allowed": [{"IPProtocol": "tcp", "ports": ["3306"]}],
        },
        {
            "name": "other-tag-allow-pg",
            "network": "projects/my-proj/global/networks/ingest-vpc",
            "direction": "INGRESS",
            "priority": 300,
            "targetTags": ["unrelated-tag"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["5432"]}],
        },
        {
            "name": "other-tag-allow-ssh",
            "network": "projects/my-proj/global/networks/ingest-vpc",
            "direction": "INGRESS",
            "priority": 300,
            "targetTags": ["unrelated-tag"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["22"]}],
        },
        {
            "name": "z-ingress-allow-pg",
            "network": "projects/my-proj/global/networks/ingest-vpc",
            "direction": "INGRESS",
            "priority": 1000,
            "sourceRanges": ["10.0.0.0/8"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["5432"]}],
        },
        {
            "name": "b-egress-deny-pg",
            "network": "projects/my-proj/global/networks/ingest-vpc",
            "direction": "EGRESS",
            "priority": 1000,
            "destinationRanges": ["10.50.0.0/16"],
            "denied": [{"IPProtocol": "tcp", "ports": ["5432"]}],
        },
        {
            "name": "a-egress-allow-https",
            "network": "projects/my-proj/global/networks/ingest-vpc",
            "direction": "EGRESS",
            "priority": 1000,
            "destinationRanges": ["0.0.0.0/0"],
            "targetServiceAccounts": ["worker@my-proj.iam.gserviceaccount.com"],
            "allowed": [{"IPProtocol": "tcp", "ports": ["443"]}],
        },
        {
            "name": "m-ingress-deny-ssh",
            "network": "projects/my-proj/global/networks/ingest-vpc",
            "direction": "INGRESS",
            "priority": 500,
            "sourceRanges": ["0.0.0.0/0"],
            "denied": [{"IPProtocol": "tcp", "ports": ["22"]}],
        },
    ]
    dns_payload = [
        {
            "name": "public-zone",
            "dnsName": "example.com.",
            "visibility": "public",
        },
        {
            "name": "bound-private-zone",
            "dnsName": "pg.internal.",
            "visibility": "private",
            "privateVisibilityConfig": {
                "networks": [
                    "not-a-dict",
                    {
                        "networkUrl": (
                            "projects/my-proj/global/networks/ingest-vpc"
                        )
                    },
                ]
            },
        },
    ]

    def _nats_handler(args):
      cmd = " ".join(args)
      if "--router=dict-nats-router" in cmd:
        return 0, "{}", ""
      return 0, json.dumps(nats_payload), ""

    runner = _FakeGcloud({
        "dataproc batches describe batch-full-net": (0, batch_payload, ""),
        "compute networks subnets describe subnet-main": (
            0,
            subnet_payload,
            "",
        ),
        "compute routers list": (0, routers_payload, ""),
        "compute routers nats list": _nats_handler,
        "compute firewall-rules list": (0, firewalls_payload, ""),
        "dns managed-zones list": (0, dns_payload, ""),
    })
    rep = spark_env_inspector.inspect_network(
        "my-proj",
        "us-central1",
        "batch",
        "batch-full-net",
        runner,
        target_port=5432,
    )
    self.assertEqual(len(rep["cloud_nats"]), 4)
    for nat_entry in rep["cloud_nats"]:
      self.assertEqual(nat_entry["router"], "ingest-router")
      self.assertTrue(nat_entry["covers_workload_subnet"], msg=nat_entry)
    self.assertEqual(rep["cloud_nats"][0]["subnetworks"], ["subnet-main"])
    self.assertEqual(rep["cloud_nats"][3]["subnetworks"], [])

    # Rules that apply to the workload are kept in evaluation order (priority,
    # then DENY before ALLOW); rules scoped to other targets are kept only
    # when they DENY or match the target port.
    self.assertEqual(
        [fw["name"] for fw in rep["firewall_rules"]],
        [
            "ingress-allow-mysql",
            "other-tag-allow-pg",
            "m-ingress-deny-ssh",
            "b-egress-deny-pg",
            "a-egress-allow-https",
            "z-ingress-allow-pg",
        ],
    )
    by_fw = {fw["name"]: fw for fw in rep["firewall_rules"]}
    self.assertTrue(by_fw["ingress-allow-mysql"]["applies_to_workload"])
    self.assertFalse(by_fw["ingress-allow-mysql"]["matches_target_port"])
    self.assertFalse(by_fw["other-tag-allow-pg"]["applies_to_workload"])
    self.assertTrue(by_fw["other-tag-allow-pg"]["matches_target_port"])
    self.assertTrue(by_fw["a-egress-allow-https"]["applies_to_workload"])
    self.assertFalse(by_fw["a-egress-allow-https"]["matches_target_port"])
    self.assertTrue(by_fw["z-ingress-allow-pg"]["applies_to_workload"])
    self.assertTrue(by_fw["z-ingress-allow-pg"]["matches_target_port"])
    self.assertEqual(
        by_fw["z-ingress-allow-pg"]["source_ranges"], ["10.0.0.0/8"]
    )
    self.assertFalse(by_fw["m-ingress-deny-ssh"]["matches_target_port"])

    self.assertEqual(
        rep["private_dns_zones"],
        [{
            "name": "bound-private-zone",
            "dns_name": "pg.internal.",
            "bound_networks": ["ingest-vpc"],
            "bound_to_workload_network": True,
        }],
    )

    # Without a configured service account the workload runs as the Compute
    # Engine default SA; rules targeting it apply, and empty strings in
    # targetServiceAccounts never match.
    runner_empty_sa = _FakeGcloud({
        "dataproc batches describe batch-empty-sa": (
            0,
            {"environmentConfig": {"executionConfig": {}}},
            "",
        ),
        "projects describe my-proj": (0, {"projectNumber": "4242"}, ""),
        "compute networks subnets describe default": (0, {}, ""),
        "compute routers list": (0, [], ""),
        "compute networks describe default": (0, {"name": "default"}, ""),
        "compute firewall-rules list": (
            0,
            [
                {
                    "name": "empty-sa-fw",
                    "network": "default",
                    "direction": "EGRESS",
                    "targetServiceAccounts": ["", "other@my-proj.iam"],
                    "denied": [{"IPProtocol": "all"}],
                },
                {
                    "name": "default-sa-fw",
                    "network": "default",
                    "direction": "EGRESS",
                    "targetServiceAccounts": [
                        "4242-compute@developer.gserviceaccount.com"
                    ],
                    "denied": [{"IPProtocol": "tcp", "ports": ["5432"]}],
                },
            ],
            "",
        ),
        "compute network-firewall-policies get-effective-firewalls": (
            0,
            {},
            "",
        ),
        "dns managed-zones list": (0, [], ""),
    })
    rep_empty_sa = spark_env_inspector.inspect_network(
        "my-proj", "us-central1", "batch", "batch-empty-sa", runner_empty_sa
    )
    self.assertEqual(rep_empty_sa["warnings"], [])
    self.assertEqual(
        rep_empty_sa["workload_service_account"],
        "4242-compute@developer.gserviceaccount.com",
    )
    self.assertTrue(rep_empty_sa["workload_service_account_inferred"])
    by_name = {fw["name"]: fw for fw in rep_empty_sa["firewall_rules"]}
    self.assertFalse(by_name["empty-sa-fw"]["applies_to_workload"])
    self.assertTrue(by_name["default-sa-fw"]["applies_to_workload"])

    # Runtime 3.0 without a service account uses end-user credentials, so the
    # VM service account (and SA-scoped rule applicability) is unknown.
    runner_euc = _FakeGcloud({
        "dataproc batches describe batch-euc": (
            0,
            {
                "runtimeConfig": {"version": "3.0"},
                "environmentConfig": {"executionConfig": {}},
            },
            "",
        ),
        "compute networks subnets describe default": (0, {}, ""),
        "compute routers list": (0, [], ""),
        "compute networks describe default": (0, {}, ""),
        "compute firewall-rules list": (
            0,
            [{
                "name": "sa-scoped-deny",
                "network": "default",
                "direction": "EGRESS",
                "targetServiceAccounts": ["any@my-proj.iam"],
                "denied": [{"IPProtocol": "all"}],
            }],
            "",
        ),
        "compute network-firewall-policies get-effective-firewalls": (
            0,
            {},
            "",
        ),
        "dns managed-zones list": (0, [], ""),
    })
    rep_euc = spark_env_inspector.inspect_network(
        "my-proj", "us-central1", "batch", "batch-euc", runner_euc
    )
    self.assertEqual(rep_euc["workload_service_account"], "")
    self.assertIsNone(rep_euc["firewall_rules"][0]["applies_to_workload"])
    self.assertNotIn(
        ["projects", "describe"], [c[:2] for c in runner_euc.calls]
    )

  def test_uri_cidr_and_port_matching_helpers(self):
    self.assertEqual(
        spark_env_inspector._parse_subnetwork_uri(
            "projects/hp/regions/us-west1/subnetworks/sub-a",
            "dp",
            "us-central1",
        ),
        ("hp", "us-west1", "sub-a"),
    )
    self.assertEqual(
        spark_env_inspector._parse_subnetwork_uri(
            "regions/us-east4/subnetworks/sub-b", "dp", "us-central1"
        ),
        ("dp", "us-east4", "sub-b"),
    )
    self.assertEqual(
        spark_env_inspector._parse_subnetwork_uri(
            "a/b/c/sub-d", "dp", "us-central1"
        ),
        ("dp", "us-central1", "sub-d"),
    )
    self.assertEqual(
        spark_env_inspector._parse_network_uri(
            "projects/hp/global/networks/vpc-a", "dp"
        ),
        ("hp", "vpc-a"),
    )
    self.assertEqual(
        spark_env_inspector._parse_network_uri("a/b/c/vpc-b", "dp"),
        ("dp", "vpc-b"),
    )

    self.assertIsNone(spark_env_inspector._cidr_usable_hosts("not-a-cidr"))
    self.assertEqual(spark_env_inspector._cidr_usable_hosts("10.0.0.5/28"), 12)
    self.assertEqual(spark_env_inspector._cidr_usable_hosts("10.0.0.0/31"), 0)

    matches = spark_env_inspector._port_matches_specs
    self.assertFalse(matches([{"IPProtocol": "udp", "ports": ["5432"]}], 5432))
    self.assertTrue(matches([{"IPProtocol": "tcp"}], 5432))
    self.assertTrue(matches([{"IPProtocol": "tcp", "ports": ["5432"]}], 5432))
    self.assertFalse(matches([{"IPProtocol": "tcp", "ports": ["5432"]}], 5433))
    self.assertFalse(matches([{"IPProtocol": "tcp", "ports": ["http"]}], 80))
    self.assertFalse(
        matches([{"IPProtocol": "tcp", "ports": ["5400-abc"]}], 5432)
    )
    self.assertFalse(
        matches([{"IPProtocol": "tcp", "ports": ["abc-5500"]}], 5432)
    )
    rng_spec = [{"IPProtocol": "tcp", "ports": ["5400-5500"]}]
    self.assertFalse(matches(rng_spec, 5399))
    self.assertTrue(matches(rng_spec, 5400))
    self.assertTrue(matches(rng_spec, 5500))
    self.assertFalse(matches(rng_spec, 5501))


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
            "mainJarFileUri": (
                "gs://my-gcp-project-code/spanner-ingest_2.12.jar"
            ),
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
    main_jar_uri = "gs://my-gcp-project-code/spanner-ingest_2.12.jar"
    self.assertEqual(report["main_jar_file_uri"], main_jar_uri)
    self.assertEqual(
        report["jar_file_uris"],
        [bq_jar, "gs://my-gcp-project-code/postgresql-42.7.3.jar"],
    )
    self.assertEqual(
        report["main_class"], "com.example.ingestion.SpannerIngestApp"
    )
    self.assertEqual(
        [item["artifact"] for item in report["classified_jars"]],
        [
            main_jar_uri,
            bq_jar,
            "gs://my-gcp-project-code/postgresql-42.7.3.jar",
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1",
        ],
    )
    by_artifact = {
        item["artifact"]: item["scala_binary_version"]
        for item in report["classified_jars"]
    }
    self.assertEqual(by_artifact[main_jar_uri], "2.12")
    self.assertEqual(by_artifact[bq_jar], "2.12")
    self.assertEqual(
        by_artifact["org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.6.1"],
        "2.12",
    )
    self.assertIsNone(
        by_artifact["gs://my-gcp-project-code/postgresql-42.7.3.jar"]
    )
    # Iceberg's runtime targets Spark 3.5 / Scala 2.12; runtime 3.0 is 4.0/2.13.
    iceberg = next(
        item
        for item in report["classified_jars"]
        if "iceberg-spark-runtime" in item["artifact"]
    )
    self.assertEqual(iceberg["spark_minor_version"], "3.5")
    self.assertFalse(iceberg["spark_matches_runtime"])
    self.assertFalse(iceberg["scala_matches_runtime"])
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
    self.assertEqual(rep_22["workload_subtype"], "pysparkJob")
    self.assertEqual(rep_22["main_python_file_uri"], "gs://bkt/job.py")
    self.assertEqual(rep_22["optional_components"], ["ICEBERG"])
    self.assertEqual(rep_22["container_image"], "")
    self.assertEqual(rep_22["runtime_spark_version"], "3.5")
    self.assertEqual(rep_22["runtime_scala_binary_version"], "2.12")
    self.assertEqual(rep_22["main_jar_file_uri"], "")
    self.assertEqual(rep_22["jar_file_uris"], ["gs://bkt/custom_2.12-1.0.jar"])
    self.assertEqual(
        rep_22["classified_jars"],
        [
            {
                "artifact": "gs://bkt/custom_2.12-1.0.jar",
                "scala_binary_version": "2.12",
                "spark_minor_version": None,
                "scala_matches_runtime": True,
                "spark_matches_runtime": None,
            }
        ],
    )
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

  def test_pyfiles_archives_container_image_sql_batch_and_prop_filtering(self):
    batch_payload = {
        "state": "DONE",
        "runtimeConfig": {
            "version": "3.0",
            "containerImage": "us-central1-docker.pkg.dev/p/repo/spark:3.0",
            "properties": {
                "spark.jars": "gs://bkt/j1.jar,gs://bkt/j2.jar",
                "spark.files": "gs://bkt/f1.cfg,gs://bkt/f2.cfg",
                "spark.submit.pyFiles": "gs://bkt/dep1.py,gs://bkt/dep2.zip",
                "spark.archives": (
                    "gs://bkt/env1.tar.gz,gs://bkt/env2.tar.gz#env"
                ),
                "spark.executor.memory": "16g",
            },
        },
        "pysparkBatch": {
            "mainPythonFileUri": "gs://bkt/etl.py",
            "jarFileUris": ["gs://bkt/j1.jar"],
            "fileUris": ["gs://bkt/f1.cfg"],
            "pythonFileUris": ["gs://bkt/dep1.py"],
            "archiveUris": ["gs://bkt/env1.tar.gz"],
        },
        "sparkBatch": {"mainClass": "com.example.ShouldNotOverrideFirstSpec"},
    }
    sql_batch_payload = {
        "state": "DONE",
        "runtimeConfig": {"version": "2.2"},
        "sparkSqlBatch": {"queryFileUri": "gs://bkt/transform.sql"},
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-py-arch": (0, batch_payload, ""),
        "dataproc batches describe batch-sql": (0, sql_batch_payload, ""),
    })
    rep = spark_env_inspector.inspect_classpath(
        "my-gcp-project", "us-central1", "batch", "batch-py-arch", runner
    )
    self.assertEqual(rep["workload_subtype"], "pysparkBatch")
    self.assertEqual(
        rep["container_image"], "us-central1-docker.pkg.dev/p/repo/spark:3.0"
    )
    self.assertEqual(rep["optional_components"], [])
    self.assertEqual(
        rep["jar_file_uris"], ["gs://bkt/j1.jar", "gs://bkt/j2.jar"]
    )
    self.assertEqual(rep["file_uris"], ["gs://bkt/f1.cfg", "gs://bkt/f2.cfg"])
    self.assertEqual(
        rep["python_file_uris"], ["gs://bkt/dep1.py", "gs://bkt/dep2.zip"]
    )
    self.assertEqual(
        rep["archive_uris"],
        ["gs://bkt/env1.tar.gz", "gs://bkt/env2.tar.gz#env"],
    )
    self.assertNotIn(
        "spark.executor.memory", rep["classpath_and_catalog_properties"]
    )

    rep_sql = spark_env_inspector.inspect_classpath(
        "my-gcp-project", "us-central1", "batch", "batch-sql", runner
    )
    self.assertEqual(rep_sql["workload_subtype"], "sparkSqlBatch")
    self.assertEqual(rep_sql["query_file_uri"], "gs://bkt/transform.sql")

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

  def test_multiline_and_none_gcloud_stderr_summarization(self):
    batch_payload = {
        "state": "FAILED",
        "runtimeConfig": {"version": "2.2"},
        "environmentConfig": {
            "executionConfig": {
                "serviceAccount": "sa@my-gcp-project.iam.gserviceaccount.com"
            }
        },
    }
    multiline_gcloud_err = (
        "WARNING: Impersonating service account.\n"
        "ERROR: (gcloud.projects.get-iam-policy) PERMISSION_DENIED: 403\n"
        "To take a quick anonymous survey, run:\n"
        "  $ gcloud survey\n"
    )
    multiline_plain_err = (
        "Connecting to Secret Manager endpoint...\n"
        "Retrying TLS handshake...\n"
        "fatal: transport connection reset\n"
        "   \n"
    )
    runner = _FakeGcloud({
        "dataproc batches describe batch-stderr": (0, batch_payload, ""),
        "projects get-iam-policy my-gcp-project": (1, "", multiline_gcloud_err),
        "secrets versions list db-pass": (1, "", multiline_plain_err),
        "secrets get-iam-policy db-pass": lambda _args: (2, "", None),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-stderr",
            "--action=identity",
            "--secret_id=db-pass",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    warnings = json.loads(stdout)["warnings"]
    self.assertEqual(
        warnings,
        [
            (
                "projects get-iam-policy 'my-gcp-project': ERROR:"
                " (gcloud.projects.get-iam-policy) PERMISSION_DENIED: 403"
            ),
            (
                "secrets versions list 'db-pass': fatal: transport connection"
                " reset"
            ),
            "secrets get-iam-policy 'db-pass': exit code 2",
        ],
    )

    code_blank, _, fatal_stderr = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-blank-err",
            "--action=identity",
        ],
        lambda _args: (3, "", "   \n\t\n"),
    )
    self.assertEqual(code_blank, 1)
    self.assertIn(
        "batches describe 'batch-blank-err': exit code 3", fatal_stderr
    )

  def test_secret_ref_fullmatch_and_runtime_prefix_anchoring(self):
    batch_payload = {
        "state": "FAILED",
        "runtimeConfig": {"version": "custom-3.0"},
        "environmentConfig": {"executionConfig": {}},
    }
    malformed_secret = "projects/sec-proj/secrets/pg-pass/extra/segment"
    runner = _FakeGcloud({
        "dataproc batches describe batch-custom-ver": (0, batch_payload, ""),
        "projects describe my-gcp-project": (
            0,
            {"projectNumber": "123456789012"},
            "",
        ),
        "projects get-iam-policy my-gcp-project": (0, {"bindings": []}, ""),
        f"secrets versions list {malformed_secret}": (0, [], ""),
        f"secrets get-iam-policy {malformed_secret}": (0, {"bindings": []}, ""),
    })

    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-custom-ver",
            "--action=identity",
            f"--secret_id={malformed_secret}",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    id_report = json.loads(stdout)
    self.assertEqual(
        id_report["user_workload_authentication_type"], "SERVICE_ACCOUNT"
    )
    self.assertEqual(
        id_report["secret_inspection"]["secret_project"], "my-gcp-project"
    )
    self.assertEqual(
        id_report["secret_inspection"]["secret_id"], malformed_secret
    )

    cp_code, cp_stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-custom-ver",
            "--action=classpath",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(cp_code, 0)
    cp_report = json.loads(cp_stdout)
    self.assertEqual(cp_report["runtime_spark_version"], "unknown")
    self.assertEqual(cp_report["runtime_scala_binary_version"], "unknown")

  def test_main_jar_deduplication_and_redaction_edge_cases(self):
    batch_payload = {
        "state": "DONE",
        "runtimeConfig": {"version": "3.0"},
        "sparkBatch": {
            "mainJarFileUri": "gs://bkt/app_2.13.jar",
            "jarFileUris": ["gs://bkt/helper.jar", "gs://bkt/app_2.13.jar"],
        },
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-dedup-jar": (0, batch_payload, ""),
    })
    code, stdout, _ = _run_cli(
        [
            "--project=my-gcp-project",
            "--batch_id=batch-dedup-jar",
            "--action=classpath",
            "--format=json",
        ],
        runner,
    )
    self.assertEqual(code, 0)
    report = json.loads(stdout)
    self.assertEqual(
        report["classified_jars"],
        [
            {
                "artifact": "gs://bkt/helper.jar",
                "scala_binary_version": None,
                "spark_minor_version": None,
                "scala_matches_runtime": None,
                "spark_matches_runtime": None,
            },
            {
                "artifact": "gs://bkt/app_2.13.jar",
                "scala_binary_version": "2.13",
                "spark_minor_version": None,
                "scala_matches_runtime": True,
                "spark_matches_runtime": None,
            },
        ],
    )

    self.assertEqual(
        spark_env_inspector.redact_value("spark.datasource.jdbc.password", ""),
        "",
    )
    self.assertEqual(
        spark_env_inspector.redact_value(
            "spark.secret_id", "projects/p/secrets/s"
        ),
        "projects/p/secrets/s",
    )
    self.assertEqual(
        spark_env_inspector.redact_value(
            "spark.app.endpoint",
            "https://api/v1?secret_id=my-sec&token=TokSecret",
        ),
        "https://api/v1?secret_id=my-sec&token=<REDACTED>",
    )
    self.assertEqual(
        spark_env_inspector.redact_value("spark.secret.pin", 12345),
        "<REDACTED>",
    )
    self.assertEqual(spark_env_inspector.redact_value("spark.port", 5432), 5432)
    self.assertIsNone(spark_env_inspector.redact_value("spark.flag", None))
    self.assertEqual(
        spark_env_inspector.redact_args([
            "gs://bkt/in.parquet",
            "gs://my-secret-bucket/tbl/dt=2026-01-01",
            "--secret_id=projects/p/secrets/s",
            "--password",
            "s3cr3t",
            "--token",
            "--next-flag",
            "plain_positional",
        ]),
        [
            "gs://bkt/in.parquet",
            "gs://my-secret-bucket/tbl/dt=2026-01-01",
            "--secret_id=projects/p/secrets/s",
            "--password",
            "<REDACTED>",
            "--token",
            "--next-flag",
            "plain_positional",
        ],
    )


class SparkEnvInspectorRunnerMarkdownAndCliTest(unittest.TestCase):

  def test_json_field_helpers_and_default_gcloud_runner(self):
    self.assertEqual(spark_env_inspector._dict_field(None, "k"), {})
    self.assertEqual(spark_env_inspector._list_field(None, "k"), [])
    self.assertEqual(spark_env_inspector._str_field(None, "k", "d"), "d")
    self.assertEqual(spark_env_inspector._str_field({"k": ""}, "k", "d"), "d")
    self.assertEqual(spark_env_inspector._str_field({"k": None}, "k", "d"), "d")

    with mock.patch.object(
        spark_env_inspector.shutil, "which", return_value=None
    ):
      with self.assertRaises(spark_env_inspector.InspectorError):
        spark_env_inspector._default_gcloud_runner(["version"])

    with mock.patch.object(
        spark_env_inspector.shutil, "which", return_value="/usr/bin/gcloud"
    ):
      with mock.patch.object(
          spark_env_inspector.subprocess,
          "run",
          return_value=subprocess.CompletedProcess(
              args=["/usr/bin/gcloud", "version", "--quiet"],
              returncode=0,
              stdout="ok-out",
              stderr="ok-err",
          ),
      ) as mock_run:
        res = spark_env_inspector._default_gcloud_runner(["version"])
        self.assertEqual(res, (0, "ok-out", "ok-err"))
        mock_run.assert_called_once_with(
            ["/usr/bin/gcloud", "version", "--quiet"],
            capture_output=True,
            text=True,
            check=False,
            timeout=spark_env_inspector._GCLOUD_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
        )

      with mock.patch.object(
          spark_env_inspector.subprocess,
          "run",
          return_value=subprocess.CompletedProcess(
              args=["/usr/bin/gcloud", "version", "--quiet"],
              returncode=2,
              stdout=None,
              stderr=None,
          ),
      ):
        self.assertEqual(
            spark_env_inspector._default_gcloud_runner(["version"]),
            (2, "", ""),
        )

      with mock.patch.object(
          spark_env_inspector.subprocess,
          "run",
          side_effect=OSError("exec failed"),
      ):
        self.assertEqual(
            spark_env_inspector._default_gcloud_runner(["version"]),
            (1, "", "exec failed"),
        )

  def test_run_gcloud_json_and_fetch_workload_error_paths(self):
    warnings = []
    self.assertEqual(
        spark_env_inspector._run_gcloud_json(
            lambda _a: (0, "   \n", ""), ["a"], warnings, "lbl"
        ),
        {},
    )
    self.assertEqual(
        spark_env_inspector._run_gcloud_json(
            lambda _a: (0, "null", ""), ["a"], warnings, "lbl"
        ),
        {},
    )
    self.assertEqual(warnings, [])

    self.assertIsNone(
        spark_env_inspector._run_gcloud_json(
            lambda _a: (0, "{bad-json", ""),
            ["a"],
            warnings,
            "iam-lbl",
            fatal=False,
        )
    )
    self.assertEqual(len(warnings), 1)
    self.assertIn("iam-lbl: invalid JSON output", warnings[0])

    with self.assertRaises(spark_env_inspector.InspectorError):
      spark_env_inspector._run_gcloud_json(
          lambda _a: (0, "{bad-json", ""),
          ["a"],
          warnings,
          "fatal-lbl",
          fatal=True,
      )

    self.assertEqual(
        spark_env_inspector.resolve_default_project(
            lambda _a: (0, "cfg-proj\n", "")
        ),
        "cfg-proj",
    )
    self.assertIsNone(
        spark_env_inspector.resolve_default_project(
            lambda _a: (1, "cfg-proj\n", "")
        )
    )
    self.assertIsNone(
        spark_env_inspector.resolve_default_project(lambda _a: (0, "  \n", ""))
    )
    self.assertIsNone(
        spark_env_inspector.resolve_default_project(
            lambda _a: (0, "(unset)\n", "")
        )
    )

    # Session fallback when gcloud prompts to install beta component.
    runner_install_beta = _FakeGcloud({
        "beta dataproc sessions describe s1": (
            1,
            "",
            "ERROR: Please run: gcloud components install beta",
        ),
        "dataproc sessions describe s1": (0, {"state": "ACTIVE"}, ""),
    })
    sess_w = []
    sess_dict, sess_cluster = spark_env_inspector._fetch_workload(
        "p", "r", "session", "s1", runner_install_beta, sess_w
    )
    self.assertEqual(sess_dict, {"state": "ACTIVE"})
    self.assertIsNone(sess_cluster)

    # Session beta NOT_FOUND raises immediately without calling GA.
    runner_sess_404 = _FakeGcloud({
        "beta dataproc sessions describe s-404": (
            1,
            "",
            "ERROR: NOT_FOUND: Session s-404 not found",
        ),
    })
    with self.assertRaisesRegex(
        spark_env_inspector.InspectorError, "Session s-404 not found"
    ):
      spark_env_inspector._fetch_workload(
          "p", "r", "session", "s-404", runner_sess_404, []
      )
    self.assertEqual(len(runner_sess_404.calls), 1)

    # Session GA fallback failure is fatal.
    runner_sess_ga_fail = _FakeGcloud({
        "beta dataproc sessions describe s-ga-fail": (
            1,
            "",
            "ERROR: Invalid choice: 'beta'",
        ),
        "dataproc sessions describe s-ga-fail": (
            1,
            "",
            "ERROR: NOT_FOUND: Session s-ga-fail",
        ),
    })
    with self.assertRaisesRegex(
        spark_env_inspector.InspectorError, "Session s-ga-fail"
    ):
      spark_env_inspector._fetch_workload(
          "p", "r", "session", "s-ga-fail", runner_sess_ga_fail, []
      )

    # Job primary describe failure is fatal; job without clusterName skips
    # cluster describe.
    runner_job_fail = _FakeGcloud({
        "dataproc jobs describe j-404": (1, "", "ERROR: NOT_FOUND: Job j-404"),
        "dataproc jobs describe j-nocluster": (
            0,
            {"status": {"state": "DONE"}},
            "",
        ),
    })
    with self.assertRaisesRegex(
        spark_env_inspector.InspectorError, "Job j-404"
    ):
      spark_env_inspector._fetch_workload(
          "p", "r", "job", "j-404", runner_job_fail, []
      )
    job_dict, cluster_dict = spark_env_inspector._fetch_workload(
        "p", "r", "job", "j-nocluster", runner_job_fail, []
    )
    self.assertEqual(job_dict, {"status": {"state": "DONE"}})
    self.assertIsNone(cluster_dict)

    with self.assertRaisesRegex(
        spark_env_inspector.InspectorError,
        "Unsupported workload kind: unsupported",
    ):
      spark_env_inspector._fetch_workload(
          "p", "r", "unsupported", "id1", runner_job_fail, []
      )

  def test_cli_argument_validation_and_default_project_resolution(self):
    noop_runner = _FakeGcloud({})
    for bad_argv in (
        ["--project=p", "--action=identity"],
        ["--project=p", "--batch_id=b1"],
        [
            "--project=p",
            "--batch_id=b1",
            "--action=network",
            "--target_port=0",
        ],
        [
            "--project=p",
            "--batch_id=b1",
            "--action=network",
            "--target_port=65536",
        ],
    ):
      with contextlib.redirect_stderr(io.StringIO()):
        with self.assertRaises(SystemExit, msg=bad_argv):
          spark_env_inspector.main(bad_argv, runner=noop_runner)

    runner_cfg = _FakeGcloud({
        "config get-value project": (0, "resolved-proj\n", ""),
        "dataproc batches describe b-cfg": (
            0,
            {"state": "DONE", "runtimeConfig": {"version": "3.0"}},
            "",
        ),
        "compute networks subnets describe default": (0, {}, ""),
        "compute routers list": (0, [], ""),
        "compute firewall-rules list": (0, [], ""),
        "dns managed-zones list": (0, [], ""),
    })
    for port in (1, 65535):
      code, stdout, _ = _run_cli(
          [
              "--batch_id=b-cfg",
              "--action=network",
              f"--target_port={port}",
              "--format=json",
          ],
          runner_cfg,
      )
      self.assertEqual(code, 0)
      parsed = json.loads(stdout)
      self.assertEqual(parsed["project"], "resolved-proj")
      self.assertEqual(parsed["target_port"], port)

  def test_format_markdown_exact_sections_for_all_actions(self):
    note_line = (
        "- note: folder/organization inheritance, group membership, and"
        " resource-level bindings (buckets, datasets, KMS keys, service"
        " accounts) are not evaluated"
    )
    id_populated = {
        "action": "identity",
        "workload_type": "job",
        "workload_id": "job-1",
        "project": "proj-a",
        "region": "us-central1",
        "cluster_name": "cl-1",
        "state": "ERROR",
        "runtime_version": "2.2",
        "state_message": "Access denied",
        "user_workload_authentication_type": "SERVICE_ACCOUNT",
        "configured_service_account": "",
        "effective_service_account": (
            "123-compute@developer.gserviceaccount.com"
        ),
        "default_service_account_inferred": True,
        "creator": "",
        "session_user": "",
        "effective_principal": (
            "serviceAccount:123-compute@developer.gserviceaccount.com"
        ),
        "kms_key": "projects/p/locations/r/keyRings/k/cryptoKeys/c",
        "staging_bucket": "stg-bkt",
        "temp_bucket": "tmp-bkt",
        "service_account_scopes": ["scope-a", "scope-b"],
        "project_iam_roles": ["roles/dataproc.worker"],
        "auth_related_properties": {"spark.sql.catalog.c": "Iceberg"},
        "secret_inspection": {
            "secret_project": "sec-p",
            "secret_id": "db-pw",
            "principal_roles_on_secret": [
                "roles/secretmanager.secretAccessor"
            ],
            "versions": [{
                "version": "1",
                "state": "ENABLED",
                "create_time": "2026-01-01T00:00:00Z",
            }],
        },
        "warnings": ["iam warning"],
    }
    self.assertEqual(
        spark_env_inspector.format_markdown(id_populated),
        "\n".join([
            "# Spark Environment Inspection (`identity`): `job-1`",
            "",
            "- workload_type: `job`",
            "- project: `proj-a`",
            "- region: `us-central1`",
            "- cluster_name: `cl-1`",
            "- state: `ERROR`",
            "- runtime_version: `2.2`",
            "- state_message: Access denied",
            "",
            "## Identity & Encryption",
            "- user_workload_authentication_type: `SERVICE_ACCOUNT`",
            (
                "- effective_principal:"
                " `serviceAccount:123-compute@developer.gserviceaccount.com`"
            ),
            "- configured_service_account: `(unset)`",
            (
                "- effective_service_account:"
                " `123-compute@developer.gserviceaccount.com`"
                " (inferred Compute Engine default SA)"
            ),
            "- kms_key: `projects/p/locations/r/keyRings/k/cryptoKeys/c`",
            "- staging_bucket: `stg-bkt`",
            "- temp_bucket: `tmp-bkt`",
            "- service_account_scopes: `scope-a`, `scope-b`",
            "",
            "## Direct Project IAM Roles on Effective Principal",
            "- `roles/dataproc.worker`",
            note_line,
            "",
            "## Auth & Catalog Properties",
            "- `spark.sql.catalog.c`: `Iceberg`",
            "",
            "## Secret Manager (`sec-p/db-pw`)",
            (
                "- principal_roles_on_secret:"
                " ['roles/secretmanager.secretAccessor']"
            ),
            "- version `1`: state=`ENABLED` (created `2026-01-01T00:00:00Z`)",
            "",
            "## Warnings (Partial Visibility)",
            "- iam warning",
        ]),
    )

    id_minimal = {
        "action": "identity",
        "workload_type": "batch",
        "workload_id": "batch-min",
        "project": "proj-a",
        "region": "us-central1",
        "cluster_name": "",
        "state": "",
        "runtime_version": "",
        "state_message": "",
        "user_workload_authentication_type": "END_USER_CREDENTIALS",
        "configured_service_account": "",
        "effective_service_account": "",
        "default_service_account_inferred": False,
        "creator": "alice@example.com",
        "session_user": "",
        "effective_principal": "user:alice@example.com",
        "kms_key": "",
        "staging_bucket": "",
        "temp_bucket": "",
        "service_account_scopes": [],
        "project_iam_roles": [],
        "auth_related_properties": {},
        "secret_inspection": {
            "secret_project": "sec-p",
            "secret_id": "db-pw",
            "principal_roles_on_secret": [],
            "versions": [],
        },
        "warnings": [],
    }
    self.assertEqual(
        spark_env_inspector.format_markdown(id_minimal),
        "\n".join([
            "# Spark Environment Inspection (`identity`): `batch-min`",
            "",
            "- workload_type: `batch`",
            "- project: `proj-a`",
            "- region: `us-central1`",
            "- state: `UNKNOWN`",
            "- runtime_version: `default`",
            "",
            "## Identity & Encryption",
            "- user_workload_authentication_type: `END_USER_CREDENTIALS`",
            "- effective_principal: `user:alice@example.com`",
            "- configured_service_account: `(unset)`",
            "- effective_service_account: `(unresolved)`",
            "- creator: `alice@example.com`",
            "- kms_key: `(none)`",
            "- staging_bucket: `(unset)`",
            "- temp_bucket: `(unset)`",
            "",
            "## Direct Project IAM Roles on Effective Principal",
            "- (none found, or IAM policy unreadable)",
            note_line,
            "",
            "## Secret Manager (`sec-p/db-pw`)",
            "- principal_roles_on_secret: (none)",
        ]),
    )

    net_populated = {
        "action": "network",
        "workload_type": "batch",
        "workload_id": "batch-net",
        "project": "proj-a",
        "region": "us-central1",
        "cluster_name": "",
        "state": "FAILED",
        "runtime_version": "3.0",
        "state_message": "",
        "effective_host_project": "host-p",
        "effective_network": "vpc-1",
        "effective_subnetwork": "sub-1",
        "internal_ip_only": True,
        "network_tags": ["tag-a"],
        "workload_service_account": "worker@proj-a.iam.gserviceaccount.com",
        "workload_service_account_inferred": False,
        "target_port": 5432,
        "subnet": {
            "ip_cidr_range": "10.0.0.0/28",
            "usable_hosts_estimate": 12,
            "private_ip_google_access": False,
        },
        "cloud_nats": [{
            "router": "rtr-1",
            "name": "nat-1",
            "source_subnetwork_ip_ranges_to_nat": (
                "ALL_SUBNETWORKS_ALL_IP_RANGES"
            ),
            "covers_workload_subnet": True,
        }],
        "vpc_peerings": [{
            "name": "to-db",
            "peer_project": "db-host",
            "peer_network": "db-vpc",
            "state": "ACTIVE",
        }],
        "firewall_policy_enforcement_order": "AFTER_CLASSIC_FIREWALL",
        "firewall_rules": [
            {
                "name": "fw-in",
                "direction": "INGRESS",
                "action": "ALLOW",
                "priority": 900,
                "source_ranges": ["10.1.0.0/16"],
                "destination_ranges": [],
                "applies_to_workload": True,
                "rules": [{"IPProtocol": "tcp", "ports": ["5432"]}],
                "matches_target_port": True,
            },
            {
                "name": "fw-out",
                "direction": "EGRESS",
                "action": "DENY",
                "priority": 1000,
                "source_ranges": [],
                "destination_ranges": ["0.0.0.0/0"],
                "applies_to_workload": False,
                "rules": [{"IPProtocol": "all"}],
                "matches_target_port": None,
            },
        ],
        "firewall_policies": [{
            "name": "org-baseline",
            "type": "HIERARCHY",
            "rules": [{
                "priority": 10,
                "direction": "EGRESS",
                "action": "deny",
                "source_ranges": [],
                "destination_ranges": ["10.50.0.0/16"],
                "layer4_configs": [{"ipProtocol": "tcp", "ports": ["5432"]}],
                "applies_to_workload": True,
                "matches_target_port": True,
            }],
        }],
        "private_dns_zones": [{
            "name": "zone-1",
            "dns_name": "db.internal.",
            "bound_to_workload_network": True,
            "bound_networks": ["vpc-1"],
        }],
        "warnings": [],
    }
    self.assertEqual(
        spark_env_inspector.format_markdown(net_populated),
        "\n".join([
            "# Spark Environment Inspection (`network`): `batch-net`",
            "",
            "- workload_type: `batch`",
            "- project: `proj-a`",
            "- region: `us-central1`",
            "- state: `FAILED`",
            "- runtime_version: `3.0`",
            "",
            "## Network Topology",
            "- effective_host_project: `host-p`",
            "- effective_network: `vpc-1`",
            "- effective_subnetwork: `sub-1`",
            "- internal_ip_only: `True`",
            "- network_tags: ['tag-a']",
            (
                "- workload_service_account:"
                " `worker@proj-a.iam.gserviceaccount.com`"
            ),
            "",
            "## Subnetwork Details",
            "- ip_cidr_range: `10.0.0.0/28`",
            "- usable_hosts_estimate: `12` (total capacity, not free IPs)",
            "- private_ip_google_access: `False`",
            "",
            "## Cloud NAT Gateways",
            (
                "- router=`rtr-1` nat=`nat-1`"
                " mode=`ALL_SUBNETWORKS_ALL_IP_RANGES`"
                " covers_workload_subnet=`True`"
            ),
            "",
            "## VPC Peerings",
            "- `to-db` -> `db-host/db-vpc` state=`ACTIVE`",
            "",
            "## Applicable VPC Firewall Rules",
            (
                "- `fw-in`: INGRESS ALLOW priority=`900`"
                " src=['10.1.0.0/16'] applies_to_workload=`True`"
                ' rules=`[{"IPProtocol": "tcp", "ports": ["5432"]}]`'
                " matches_port_5432=`True`"
            ),
            (
                "- `fw-out`: EGRESS DENY priority=`1000`"
                " dest=['0.0.0.0/0'] applies_to_workload=`False`"
                ' rules=`[{"IPProtocol": "all"}]`'
            ),
            "",
            "## Firewall Policies",
            (
                "- network_firewall_policy_enforcement_order:"
                " `AFTER_CLASSIC_FIREWALL`"
            ),
            "- policy `org-baseline` (HIERARCHY):",
            (
                "  - priority=`10` EGRESS deny dest=['10.50.0.0/16']"
                ' l4=`[{"ipProtocol": "tcp", "ports": ["5432"]}]`'
                " applies_to_workload=`True` matches_port_5432=`True`"
            ),
            "",
            "## Private Cloud DNS Zones",
            (
                "- `zone-1` (`db.internal.`):"
                " bound_to_workload_network=`True` bound_networks=['vpc-1']"
            ),
        ]),
    )

    net_minimal = {
        "action": "network",
        "workload_type": "batch",
        "workload_id": "batch-net-min",
        "project": "proj-a",
        "region": "us-central1",
        "state": "DONE",
        "runtime_version": "3.0",
        "effective_host_project": "proj-a",
        "effective_network": "default",
        "effective_subnetwork": "default",
        "internal_ip_only": True,
        "network_tags": [],
        "target_port": None,
        "subnet": None,
        "cloud_nats": [],
        "firewall_rules": [],
        "private_dns_zones": [],
        "warnings": [],
    }
    self.assertEqual(
        spark_env_inspector.format_markdown(net_minimal),
        "\n".join([
            "# Spark Environment Inspection (`network`): `batch-net-min`",
            "",
            "- workload_type: `batch`",
            "- project: `proj-a`",
            "- region: `us-central1`",
            "- state: `DONE`",
            "- runtime_version: `3.0`",
            "",
            "## Network Topology",
            "- effective_host_project: `proj-a`",
            "- effective_network: `default`",
            "- effective_subnetwork: `default`",
            "- internal_ip_only: `True`",
            "- network_tags: []",
            "- workload_service_account: `(unknown)`",
            "",
            "## Cloud NAT Gateways",
            "- (no Cloud NAT gateways on workload network/region)",
            "",
            "## VPC Peerings",
            "- (no VPC peerings on workload network)",
            "",
            "## Applicable VPC Firewall Rules",
            "- (no matching VPC firewall rules returned)",
            "",
            "## Firewall Policies",
            (
                "- (no hierarchical, network, or system firewall policies"
                " returned)"
            ),
            "",
            "## Private Cloud DNS Zones",
            "- (no private Cloud DNS zones found)",
        ]),
    )

    cp_populated = {
        "action": "classpath",
        "workload_type": "batch",
        "workload_id": "batch-cp",
        "project": "proj-a",
        "region": "us-central1",
        "state": "FAILED",
        "runtime_version": "3.0",
        "workload_subtype": "sparkBatch",
        "runtime_spark_version": "4.0",
        "runtime_scala_binary_version": "2.13",
        "optional_components": ["ICEBERG"],
        "container_image": "gcr.io/p/img:1",
        "main_python_file_uri": "gs://bkt/main.py",
        "notebook_file_uri": "gs://bkt/nb.ipynb",
        "main_jar_file_uri": "gs://bkt/app_2.12.jar",
        "main_class": "com.example.App",
        "query_file_uri": "gs://bkt/q.sql",
        "args": ["--env=prod"],
        "classified_jars": [
            {
                "artifact": "gs://bkt/app_2.12.jar",
                "scala_binary_version": "2.12",
                "spark_minor_version": None,
                "scala_matches_runtime": False,
                "spark_matches_runtime": None,
            },
            {
                "artifact": "gs://bkt/spark-3.5-bigquery-0.42.0.jar",
                "scala_binary_version": None,
                "spark_minor_version": "3.5",
                "scala_matches_runtime": None,
                "spark_matches_runtime": False,
            },
        ],
        "file_uris": ["gs://bkt/f.cfg"],
        "python_file_uris": ["gs://bkt/u.py"],
        "archive_uris": ["gs://bkt/a.tgz"],
        "classpath_and_catalog_properties": {"spark.sql.ansi.enabled": "true"},
        "warnings": [],
    }
    self.assertEqual(
        spark_env_inspector.format_markdown(cp_populated),
        "\n".join([
            "# Spark Environment Inspection (`classpath`): `batch-cp`",
            "",
            "- workload_type: `batch`",
            "- project: `proj-a`",
            "- region: `us-central1`",
            "- state: `FAILED`",
            "- runtime_version: `3.0`",
            "",
            "## Runtime & Entrypoint",
            "- workload_subtype: `sparkBatch`",
            "- runtime_spark_version: `4.0`",
            "- runtime_scala_binary_version: `2.13`",
            "- optional_components: ['ICEBERG']",
            "- container_image: `gcr.io/p/img:1`",
            "- main_python_file_uri: `gs://bkt/main.py`",
            "- notebook_file_uri: `gs://bkt/nb.ipynb`",
            "- main_jar_file_uri: `gs://bkt/app_2.12.jar`",
            "- main_class: `com.example.App`",
            "- query_file_uri: `gs://bkt/q.sql`",
            '- args: `["--env=prod"]`',
            "",
            "## Attached JARs & Packages",
            (
                "- `gs://bkt/app_2.12.jar` (scala_binary=`2.12`"
                " scala_matches_runtime=`False` spark_minor=`n/a`"
                " spark_matches_runtime=`None`)"
            ),
            (
                "- `gs://bkt/spark-3.5-bigquery-0.42.0.jar`"
                " (scala_binary=`unversioned` scala_matches_runtime=`None`"
                " spark_minor=`3.5` spark_matches_runtime=`False`)"
            ),
            "",
            "## Distributed Files, PyFiles & Archives",
            "- file_uris: ['gs://bkt/f.cfg']",
            "- python_file_uris: ['gs://bkt/u.py']",
            "- archive_uris: ['gs://bkt/a.tgz']",
            "",
            "## Classpath, SQL & Catalog Properties",
            "- `spark.sql.ansi.enabled`: `true`",
        ]),
    )

    cp_minimal = {
        "action": "classpath",
        "workload_type": "batch",
        "workload_id": "batch-cp-min",
        "project": "proj-a",
        "region": "us-central1",
        "state": "DONE",
        "runtime_version": "3.0",
        "workload_subtype": "",
        "runtime_spark_version": "4.0",
        "runtime_scala_binary_version": "2.13",
        "optional_components": [],
        "container_image": "",
        "main_python_file_uri": "",
        "notebook_file_uri": "",
        "main_jar_file_uri": "",
        "main_class": "",
        "query_file_uri": "",
        "args": [],
        "classified_jars": [],
        "file_uris": [],
        "python_file_uris": [],
        "archive_uris": [],
        "classpath_and_catalog_properties": {},
        "warnings": [],
    }
    self.assertEqual(
        spark_env_inspector.format_markdown(cp_minimal),
        "\n".join([
            "# Spark Environment Inspection (`classpath`): `batch-cp-min`",
            "",
            "- workload_type: `batch`",
            "- project: `proj-a`",
            "- region: `us-central1`",
            "- state: `DONE`",
            "- runtime_version: `3.0`",
            "",
            "## Runtime & Entrypoint",
            "- workload_subtype: `unknown`",
            "- runtime_spark_version: `4.0`",
            "- runtime_scala_binary_version: `2.13`",
            "- optional_components: []",
            "- container_image: `(default image)`",
            "",
            "## Attached JARs & Packages",
            "- (no custom JARs or spark.jars.packages attached)",
            "",
            "## Distributed Files, PyFiles & Archives",
            "- file_uris: []",
            "- python_file_uris: []",
            "- archive_uris: []",
        ]),
    )


class SparkEnvInspectorFixesTest(unittest.TestCase):
  """Covers principals, policies, ABI checks, and redaction edge cases."""

  def test_end_user_credentials_principal_and_project_roles(self):
    alice_member = "user:alice@example.com"
    batch_payload = {
        "state": "FAILED",
        "creator": "alice@example.com",
        "runtimeConfig": {"version": "3.0"},
        "environmentConfig": {"executionConfig": {}},
    }
    session_payload = {
        "state": "ACTIVE",
        "creator": "pipeline@my-proj.iam.gserviceaccount.com",
        "user": "bob@example.com",
        "runtimeConfig": {"version": "3.0"},
        "sparkConnectSession": {},
    }
    iam_payload = {
        "bindings": [
            {
                "role": "roles/dataproc.serverlessEditor",
                "members": [alice_member],
            },
            {"role": "roles/storage.objectViewer", "members": ["group:eng"]},
        ]
    }
    runner = _FakeGcloud({
        "dataproc batches describe batch-euc": (0, batch_payload, ""),
        "beta dataproc sessions describe sess-euc": (0, session_payload, ""),
        "projects get-iam-policy my-proj": (0, iam_payload, ""),
    })
    rep = spark_env_inspector.inspect_identity(
        "my-proj", "us-central1", "batch", "batch-euc", runner
    )
    self.assertEqual(
        rep["user_workload_authentication_type"], "END_USER_CREDENTIALS"
    )
    self.assertEqual(rep["effective_service_account"], "")
    self.assertEqual(rep["effective_principal"], alice_member)
    self.assertEqual(
        rep["project_iam_roles"], ["roles/dataproc.serverlessEditor"]
    )
    # Sessions act as their owner (`user`), not as the creator.
    sess = spark_env_inspector.inspect_identity(
        "my-proj", "us-central1", "session", "sess-euc", runner
    )
    self.assertEqual(sess["session_user"], "bob@example.com")
    self.assertEqual(sess["effective_principal"], "user:bob@example.com")
    self.assertEqual(
        spark_env_inspector._member_for_email("x@p.iam.gserviceaccount.com"),
        "serviceAccount:x@p.iam.gserviceaccount.com",
    )

  def test_cluster_kms_key_falls_back_to_encryption_config_kms_key(self):
    runner = _FakeGcloud({
        "dataproc jobs describe j-kms": (
            0,
            {"placement": {"clusterName": "c-kms"}},
            "",
        ),
        "dataproc clusters describe c-kms": (
            0,
            {
                "config": {
                    "encryptionConfig": {
                        "kmsKey": (
                            "projects/p/locations/r/keyRings/k/cryptoKeys/c"
                        )
                    },
                    "gceClusterConfig": {
                        "serviceAccount": "sa@p.iam.gserviceaccount.com"
                    },
                }
            },
            "",
        ),
        "projects get-iam-policy p": (0, {"bindings": []}, ""),
    })
    rep = spark_env_inspector.inspect_identity(
        "p", "us-central1", "job", "j-kms", runner
    )
    self.assertEqual(
        rep["kms_key"], "projects/p/locations/r/keyRings/k/cryptoKeys/c"
    )

  def test_spark_minor_detection_and_notebook_batch(self):
    detect = spark_env_inspector._detect_spark_minor
    self.assertEqual(detect("gs://b/spark-3.5-bigquery-0.42.0.jar"), "3.5")
    self.assertEqual(
        detect("org.apache.iceberg:iceberg-spark-runtime-4.0_2.13:1.10.0"),
        "4.0",
    )
    self.assertEqual(
        detect("gs://b/hudi-spark3.5-bundle_2.12-0.15.0.jar"), "3.5"
    )
    self.assertEqual(
        detect("gs://spark-lib/spanner/spark-4.0-spanner-1.2.0.jar"), "4.0"
    )
    self.assertIsNone(
        detect("gs://b/spark-bigquery-with-dependencies_2.12-0.41.0.jar")
    )
    self.assertIsNone(
        detect("org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0")
    )
    self.assertIsNone(detect("gs://b/postgresql-42.7.3.jar"))
    self.assertIsNone(spark_env_inspector._matches_runtime("3.5", "unknown"))

    batch_payload = {
        "runtimeConfig": {"version": "2.2"},
        "pysparkNotebookBatch": {
            "notebookFileUri": "gs://b/explore.ipynb",
            "jarFileUris": ["gs://b/spark-3.3-bigquery-0.30.0.jar"],
        },
    }
    runner = _FakeGcloud({
        "dataproc batches describe nb-batch": (0, batch_payload, ""),
    })
    rep = spark_env_inspector.inspect_classpath(
        "p", "us-central1", "batch", "nb-batch", runner
    )
    self.assertEqual(rep["workload_subtype"], "pysparkNotebookBatch")
    self.assertEqual(rep["notebook_file_uri"], "gs://b/explore.ipynb")
    self.assertEqual(rep["classified_jars"][0]["spark_minor_version"], "3.3")
    self.assertFalse(rep["classified_jars"][0]["spark_matches_runtime"])

  def test_firewall_policy_summary(self):
    batch_payload = {
        "runtimeConfig": {"version": "2.2"},
        "environmentConfig": {
            "executionConfig": {
                "subnetworkUri": "regions/us-central1/subnetworks/sub-a",
                "serviceAccount": "etl@p.iam.gserviceaccount.com",
            }
        },
    }
    many_ranges = [f"10.0.{i}.0/24" for i in range(8)]
    policies_payload = {
        "firewalls": [],
        "firewallPolicys": [
            {
                "name": "123456",
                "type": "HIERARCHY",
                "rules": [
                    {
                        "priority": 40,
                        "direction": "EGRESS",
                        "action": "deny",
                        "match": {
                            "destIpRanges": ["0.0.0.0/0"],
                            "layer4Configs": [{"ipProtocol": "all"}],
                        },
                    },
                    {
                        "priority": 30,
                        "direction": "EGRESS",
                        "action": "goto_next",
                        "match": {
                            "destIpRanges": many_ranges,
                            "layer4Configs": [{"ipProtocol": "tcp"}],
                        },
                    },
                    {
                        "priority": 35,
                        "direction": "INGRESS",
                        "action": "allow",
                        "disabled": True,
                        "match": {"srcIpRanges": ["1.2.3.4/32"]},
                    },
                ],
            },
            {
                "name": "dataproc-fw-123-us-central1",
                "shortName": "dataproc-fw-123-us-central1",
                "type": "SYSTEM_REGIONAL",
                "rules": [{
                    "priority": 4,
                    "direction": "INGRESS",
                    "action": "allow",
                    "targetSecureTags": [{"name": "tagValues/987"}],
                    "match": {
                        "layer4Configs": [{"ipProtocol": "tcp"}],
                        "srcSecureTags": [{"name": "tagValues/987"}],
                    },
                }],
            },
            {
                "name": "net-policy",
                "type": "NETWORK",
                "rules": [{
                    "priority": 100,
                    "direction": "EGRESS",
                    "action": "deny",
                    "targetServiceAccounts": [
                        "other@p.iam.gserviceaccount.com"
                    ],
                    "match": {
                        "destIpRanges": ["10.20.0.0/16"],
                        "layer4Configs": [
                            {"ipProtocol": "tcp", "ports": ["5432"]}
                        ],
                    },
                }],
            },
        ],
    }
    runner = _FakeGcloud({
        "dataproc batches describe b-pol": (0, batch_payload, ""),
        "compute networks subnets describe sub-a": (
            0,
            {"name": "sub-a", "network": "projects/p/global/networks/vpc-a"},
            "",
        ),
        "compute routers list": (0, [], ""),
        "compute networks describe vpc-a": (0, {"name": "vpc-a"}, ""),
        "compute firewall-rules list": (0, [], ""),
        "compute network-firewall-policies get-effective-firewalls": (
            0,
            policies_payload,
            "",
        ),
        "dns managed-zones list": (0, [], ""),
    })
    rep = spark_env_inspector.inspect_network(
        "p", "us-central1", "batch", "b-pol", runner, target_port=5432
    )
    self.assertEqual(rep["warnings"], [])
    hier, system, net = rep["firewall_policies"]
    self.assertEqual(hier["type"], "HIERARCHY")
    # Disabled rules are skipped; the rest are listed in priority order.
    self.assertEqual([r["priority"] for r in hier["rules"]], [30, 40])
    self.assertEqual(hier["rules"][0]["action"], "goto_next")
    self.assertEqual(
        hier["rules"][0]["destination_ranges"],
        [*many_ranges[:5], "... (+3 more)"],
    )
    self.assertTrue(hier["rules"][0]["matches_target_port"])
    self.assertEqual(system["name"], "dataproc-fw-123-us-central1")
    self.assertIsNone(system["rules"][0]["applies_to_workload"])
    self.assertEqual(
        system["rules"][0]["target_secure_tags"], ["tagValues/987"]
    )
    self.assertFalse(net["rules"][0]["applies_to_workload"])
    self.assertTrue(net["rules"][0]["matches_target_port"])
    # The effective-firewalls query is regional (the subnet's region).
    self.assertIn(
        [
            "compute",
            "network-firewall-policies",
            "get-effective-firewalls",
            "--network=vpc-a",
            "--region=us-central1",
            "--project=p",
            "--format=json",
        ],
        runner.calls,
    )

    with mock.patch.object(spark_env_inspector, "_MAX_POLICY_RULES", 1):
      capped = spark_env_inspector.inspect_network(
          "p", "us-central1", "batch", "b-pol", runner
      )
    self.assertEqual(
        sum(len(p["rules"]) for p in capped["firewall_policies"]), 1
    )
    self.assertIn("only the first 1 rules", capped["warnings"][-1])

  def test_oracle_credentials_are_redacted(self):
    self.assertEqual(
        spark_env_inspector.redact_value(
            "spark.datasource.jdbc.url",
            "jdbc:oracle:thin:scott/tiger@//db:1521/ORCL",
        ),
        "jdbc:oracle:thin:scott/<REDACTED>@//db:1521/ORCL",
    )
    self.assertEqual(
        spark_env_inspector.redact_args(
            ["--jdbc-url=jdbc:oracle:oci:etl/S3cret!@db"]
        ),
        ["--jdbc-url=jdbc:oracle:oci:etl/<REDACTED>@db"],
    )

  def test_resource_values_after_sensitive_flags_are_kept(self):
    self.assertEqual(
        spark_env_inspector.redact_args([
            "--use-secret-manager",
            "gs://bkt/input.csv",
            "--db-password",
            "hunter2",
            "--token",
            "https://etl:pw@host/path",
            "--secret",
            "projects/p/secrets/db/versions/2",
        ]),
        [
            "--use-secret-manager",
            "gs://bkt/input.csv",
            "--db-password",
            "<REDACTED>",
            "--token",
            "https://etl:<REDACTED>@host/path",
            "--secret",
            "projects/p/secrets/db/versions/2",
        ],
    )

  def test_multi_tenant_and_personal_auth_clusters_warn(self):
    runner = _FakeGcloud({
        "dataproc jobs describe j-mt": (
            0,
            {"placement": {"clusterName": "c-mt"}},
            "",
        ),
        "dataproc clusters describe c-mt": (
            0,
            {
                "config": {
                    "gceClusterConfig": {
                        "serviceAccount": "vm@p.iam.gserviceaccount.com"
                    },
                    "securityConfig": {
                        "identityConfig": {
                            "userServiceAccountMapping": {
                                "alice@example.com": (
                                    "alice-sa@p.iam.gserviceaccount.com"
                                ),
                            }
                        }
                    },
                    "softwareConfig": {
                        "properties": {
                            "dataproc:dataproc.personal-auth.user": (
                                "bob@example.com"
                            )
                        }
                    },
                }
            },
            "",
        ),
        "projects get-iam-policy p": (0, {"bindings": []}, ""),
    })
    rep = spark_env_inspector.inspect_identity(
        "p", "us-central1", "job", "j-mt", runner
    )
    self.assertEqual(
        rep["effective_service_account"], "vm@p.iam.gserviceaccount.com"
    )
    self.assertEqual(len(rep["warnings"]), 2)
    self.assertIn("secure multi-tenancy (1 user mappings)", rep["warnings"][0])
    self.assertIn("'bob@example.com'", rep["warnings"][1])

  def test_missing_gcloud_without_project_returns_error(self):
    with mock.patch.object(
        spark_env_inspector.shutil, "which", return_value=None
    ):
      code, _, stderr = _run_cli(
          ["--batch_id=b1", "--action=identity"],
          spark_env_inspector._default_gcloud_runner,
      )
    self.assertEqual(code, 1)
    self.assertIn("not installed", stderr)


_VERDICT_NETWORK_URI = "projects/p/global/networks/vpc-v"


def _policy(name, policy_type, rules):
  return {"name": name, "type": policy_type, "rules": rules}


def _policy_rule(
    priority,
    action,
    *,
    direction="EGRESS",
    l4=None,
    dest=None,
    src=None,
    match_extra=None,
    **extra,
):
  match = {"layer4Configs": l4 or [{"ipProtocol": "all"}]}
  if dest is not None:
    match["destIpRanges"] = dest
  if src is not None:
    match["srcIpRanges"] = src
  match.update(match_extra or {})
  rule = {
      "priority": priority,
      "direction": direction,
      "action": action,
      "match": match,
  }
  rule.update(extra)
  return rule


def _vpc_rule(name, priority, *, direction="EGRESS", denied=None, **extra):
  rule = {
      "name": name,
      "network": _VERDICT_NETWORK_URI,
      "direction": direction,
      "priority": priority,
  }
  if denied is not None:
    rule["denied"] = denied
  else:
    rule["allowed"] = extra.pop("allowed", [{"IPProtocol": "all"}])
  rule.update(extra)
  return rule


def _verdict_runner(
    *,
    vpc_rules=(),
    policies=(),
    network=None,
    network_code=0,
    firewalls_code=0,
    policies_code=0,
    stack_type="IPV4_ONLY",
):
  batch_payload = {
      "runtimeConfig": {"version": "2.2"},
      "environmentConfig": {
          "executionConfig": {
              "subnetworkUri": "regions/us-central1/subnetworks/sub-v",
              "serviceAccount": "etl@p.iam.gserviceaccount.com",
              "networkTags": ["spark"],
          }
      },
  }
  subnet_payload = {
      "name": "sub-v",
      "network": _VERDICT_NETWORK_URI,
      "ipCidrRange": "10.8.0.0/24",
      "stackType": stack_type,
  }

  def _response(code, payload):
    return (
        code,
        payload if code == 0 else "",
        "ERROR: (gcloud) 403" if code else "",
    )

  return _FakeGcloud({
      "dataproc batches describe b-fw": (0, batch_payload, ""),
      "compute networks subnets describe sub-v": (0, subnet_payload, ""),
      "compute routers list": (0, [], ""),
      "compute networks describe vpc-v": _response(
          network_code, network or {"name": "vpc-v"}
      ),
      "compute firewall-rules list": _response(firewalls_code, list(vpc_rules)),
      "compute network-firewall-policies get-effective-firewalls": _response(
          policies_code, {"firewallPolicys": list(policies), "firewalls": []}
      ),
      "dns managed-zones list": (0, [], ""),
  })


def _verdict(runner, target_port=443, **kwargs):
  rep = spark_env_inspector.inspect_network(
      "p", "us-central1", "batch", "b-fw", runner, target_port, **kwargs
  )
  return rep["firewall_verdict"]


class SparkEnvInspectorFirewallVerdictTest(unittest.TestCase):

  def test_goto_next_hands_off_and_lower_priority_deny_is_skipped(self):
    hierarchy = _policy(
        "folder-policy",
        "HIERARCHY",
        [
            _policy_rule(38, "deny", dest=["0.0.0.0/0"]),
            _policy_rule(
                31,
                "goto_next",
                dest=["0.0.0.0/0"],
                l4=[{"ipProtocol": "tcp"}, {"ipProtocol": "icmp"}],
            ),
            _policy_rule(10, "deny", direction="INGRESS", src=["0.0.0.0/0"]),
        ],
    )
    runner = _verdict_runner(policies=[hierarchy])
    verdict = _verdict(runner)
    self.assertEqual(verdict["verdict"], "ALLOWED")
    self.assertEqual(
        verdict["decided_by"],
        {
            "stage": "implied rules",
            "priority": 65535,
            "rule": "implied allow egress",
            "action": "allow",
        },
    )
    self.assertEqual(
        verdict["evaluation_order"],
        [
            "hierarchical policy `folder-policy`",
            "VPC firewall rules",
            "implied rules",
        ],
    )
    first = verdict["stages"][0]["first_match"]
    self.assertEqual(
        (first["priority"], first["action"], first["match"]),
        (31, "goto_next", "match"),
    )
    self.assertIsNone(verdict["stages"][1]["first_match"])
    self.assertEqual(verdict["unevaluated_rules"], [])
    self.assertEqual(verdict["ip_version"], 4)

    # UDP is not covered by the goto_next rule, so the deny-all decides.
    udp = _verdict(runner, target_protocol="udp")
    self.assertEqual(udp["verdict"], "DENIED")
    self.assertEqual(
        (udp["decided_by"]["stage"], udp["decided_by"]["priority"]),
        ("hierarchical policy `folder-policy`", 38),
    )

  def test_vpc_rules_tie_breaks_and_target_scoping(self):
    vpc_rules = [
        _vpc_rule(
            "allow-db",
            900,
            destinationRanges=["10.50.0.0/16"],
            allowed=[{"IPProtocol": "tcp", "ports": ["5432"]}],
            targetTags=["spark"],
        ),
        _vpc_rule(
            "deny-db",
            900,
            destinationRanges=["10.50.0.0/16"],
            denied=[{"IPProtocol": "tcp", "ports": ["5400-5500"]}],
        ),
        _vpc_rule(
            "deny-other-tag",
            100,
            denied=[{"IPProtocol": "all"}],
            targetTags=["unrelated"],
        ),
        _vpc_rule(
            "deny-other-sa",
            100,
            denied=[{"IPProtocol": "all"}],
            targetServiceAccounts=["other@p.iam.gserviceaccount.com"],
        ),
        _vpc_rule(
            "deny-disabled", 50, denied=[{"IPProtocol": "all"}], disabled=True
        ),
    ]
    runner = _verdict_runner(vpc_rules=vpc_rules)
    verdict = _verdict(runner, target_port=5432, target_ip="10.50.1.2")
    self.assertEqual(verdict["verdict"], "DENIED")
    self.assertEqual(verdict["decided_by"]["rule"], "deny-db")
    self.assertEqual(verdict["stages"][0]["first_match"]["rule"], "deny-db")
    other = _verdict(runner, target_port=5432, target_ip="192.168.7.7")
    self.assertEqual(other["verdict"], "ALLOWED")
    self.assertEqual(other["decided_by"]["stage"], "implied rules")

  def test_destination_specific_rule_needs_target_ip(self):
    runner = _verdict_runner(
        vpc_rules=[
            _vpc_rule(
                "deny-db",
                900,
                destinationRanges=["10.50.0.0/16"],
                denied=[{"IPProtocol": "tcp", "ports": ["5432"]}],
            )
        ]
    )
    verdict = _verdict(runner, target_port=5432)
    self.assertEqual(verdict["verdict"], "INDETERMINATE")
    self.assertEqual(verdict["possible_outcomes"], ["ALLOWED", "DENIED"])
    self.assertIsNone(verdict["decided_by"])
    (unevaluated,) = verdict["unevaluated_rules"]
    self.assertEqual(unevaluated["rule"], "deny-db")
    self.assertEqual(unevaluated["match"], "indeterminate")
    self.assertIn("pass --target_ip", unevaluated["reasons"][0])
    self.assertEqual(
        _verdict(runner, target_port=5432, target_ip="10.50.9.9")["verdict"],
        "DENIED",
    )
    self.assertEqual(_verdict(runner, target_port=5433)["verdict"], "ALLOWED")

  def test_verdict_is_definite_when_every_outcome_agrees(self):
    system = _policy(
        "dataproc-fw-1",
        "SYSTEM_REGIONAL",
        [
            _policy_rule(
                4,
                "allow",
                dest=["0.0.0.0/0"],
                targetSecureTags=[{"name": "tagValues/1"}],
            )
        ],
    )
    verdict = _verdict(_verdict_runner(policies=[system]))
    self.assertEqual(verdict["verdict"], "ALLOWED")
    # The deciding rule depends on the secure tag, so none is reported.
    self.assertIsNone(verdict["decided_by"])
    (unevaluated,) = verdict["unevaluated_rules"]
    self.assertIn("targets secure tags", unevaluated["reasons"][0])

    denying = _verdict(
        _verdict_runner(
            policies=[system],
            vpc_rules=[
                _vpc_rule("deny-all", 1000, denied=[{"IPProtocol": "all"}])
            ],
        )
    )
    self.assertEqual(denying["verdict"], "INDETERMINATE")

  def test_unresolved_selectors_and_l7_inspection_are_indeterminate(self):
    fqdn = _policy(
        "net-pol",
        "NETWORK",
        [
            _policy_rule(
                100,
                "deny",
                match_extra={"destFqdns": ["s3.amazonaws.com"]},
            )
        ],
    )
    verdict = _verdict(_verdict_runner(policies=[fqdn]), target_ip="52.1.2.3")
    self.assertEqual(verdict["verdict"], "INDETERMINATE")
    self.assertIn("destFqdns", verdict["unevaluated_rules"][0]["reasons"][0])

    l7 = _policy(
        "net-pol",
        "NETWORK",
        [
            _policy_rule(
                100,
                "apply_security_profile_group",
                dest=["0.0.0.0/0"],
                securityProfileGroup="spg-1",
            )
        ],
    )
    inspected = _verdict(_verdict_runner(policies=[l7]))
    self.assertEqual(inspected["verdict"], "INDETERMINATE")
    self.assertEqual(inspected["possible_outcomes"], ["UNEVALUATED"])

  def test_network_policy_enforcement_order(self):
    vpc_rules = [
        _vpc_rule(
            "allow-https",
            1000,
            allowed=[{"IPProtocol": "tcp", "ports": ["443"]}],
        )
    ]
    policies = [
        _policy(
            "global-pol",
            "NETWORK",
            [_policy_rule(100, "deny", dest=["0.0.0.0/0"])],
        )
    ]
    after = _verdict(
        _verdict_runner(
            vpc_rules=vpc_rules,
            policies=policies,
            network={
                "name": "vpc-v",
                "networkFirewallPolicyEnforcementOrder": (
                    "AFTER_CLASSIC_FIREWALL"
                ),
            },
        )
    )
    self.assertEqual(
        (after["verdict"], after["decided_by"]["rule"]),
        ("ALLOWED", "allow-https"),
    )
    before = _verdict(
        _verdict_runner(
            vpc_rules=vpc_rules,
            policies=policies,
            network={
                "name": "vpc-v",
                "networkFirewallPolicyEnforcementOrder": (
                    "BEFORE_CLASSIC_FIREWALL"
                ),
            },
        )
    )
    self.assertEqual(before["verdict"], "DENIED")
    self.assertEqual(
        before["evaluation_order"],
        [
            "global network policy `global-pol`",
            "VPC firewall rules",
            "implied rules",
        ],
    )
    unknown = _verdict(
        _verdict_runner(vpc_rules=vpc_rules, policies=policies, network_code=1)
    )
    self.assertEqual(unknown["verdict"], "INDETERMINATE")
    self.assertIn("both network firewall policy", " ".join(unknown["notes"]))

  def test_order_of_several_hierarchical_policies_is_not_assumed(self):
    allow = _policy(
        "org-pol", "HIERARCHY", [_policy_rule(10, "allow", dest=["0.0.0.0/0"])]
    )
    deny = _policy(
        "folder-pol",
        "HIERARCHY",
        [_policy_rule(10, "deny", dest=["0.0.0.0/0"])],
    )
    conflicting = _verdict(_verdict_runner(policies=[allow, deny]))
    self.assertEqual(conflicting["verdict"], "INDETERMINATE")
    notes = " ".join(conflicting["notes"])
    self.assertIn("order of the 2 hierarchical policies", notes)
    self.assertIn("results differ", notes)

    hand_off = _policy(
        "org-pol",
        "HIERARCHY",
        [_policy_rule(10, "goto_next", dest=["0.0.0.0/0"])],
    )
    agreeing = _verdict(_verdict_runner(policies=[hand_off, deny]))
    self.assertEqual(agreeing["verdict"], "DENIED")
    self.assertEqual(
        agreeing["decided_by"]["stage"], "hierarchical policy `folder-pol`"
    )

  def test_unreadable_inputs(self):
    no_policies = _verdict(_verdict_runner(policies_code=1))
    self.assertEqual(no_policies["verdict"], "INDETERMINATE")
    self.assertEqual(
        no_policies["stages"][0],
        {"stage": "firewall policies", "readable": False, "first_match": None},
    )
    # A hierarchical deny decides before the unreadable VPC rules.
    deny = _policy(
        "org-pol", "HIERARCHY", [_policy_rule(10, "deny", dest=["0.0.0.0/0"])]
    )
    decided = _verdict(_verdict_runner(policies=[deny], firewalls_code=1))
    self.assertEqual(decided["verdict"], "DENIED")
    self.assertFalse(decided["stages"][1]["readable"])
    unknown_type = _verdict(
        _verdict_runner(
            policies=[
                _policy(
                    "odd", "", [_policy_rule(5, "deny", dest=["0.0.0.0/0"])]
                )
            ]
        )
    )
    self.assertEqual(unknown_type["verdict"], "INDETERMINATE")
    self.assertIn("unrecognized type", " ".join(unknown_type["notes"]))

  def test_ingress_ipv6_and_workload_side_ranges(self):
    intra_subnet = _vpc_rule(
        "allow-intra",
        65534,
        direction="INGRESS",
        sourceRanges=["10.8.0.0/24"],
        allowed=[{"IPProtocol": "tcp"}],
    )
    runner = _verdict_runner(vpc_rules=[intra_subnet])
    self.assertEqual(
        _verdict(
            runner,
            target_port=7337,
            target_ip="10.8.0.5",
            target_direction="ingress",
        )["decided_by"]["rule"],
        "allow-intra",
    )
    outside = _verdict(
        runner,
        target_port=7337,
        target_ip="10.9.0.5",
        target_direction="ingress",
    )
    self.assertEqual(outside["verdict"], "DENIED")
    self.assertEqual(outside["decided_by"]["rule"], "implied deny ingress")
    tagged = _verdict(
        _verdict_runner(
            vpc_rules=[
                _vpc_rule(
                    "allow-tagged",
                    1000,
                    direction="INGRESS",
                    sourceTags=["bastion"],
                )
            ]
        ),
        target_port=22,
        target_ip="10.9.0.5",
        target_direction="ingress",
    )
    self.assertEqual(tagged["verdict"], "INDETERMINATE")
    self.assertIn("source tags", tagged["unevaluated_rules"][0]["reasons"][0])

    ipv6_deny = _policy(
        "net-pol", "NETWORK", [_policy_rule(10, "deny", dest=["::/0"])]
    )
    self.assertEqual(
        _verdict(_verdict_runner(policies=[ipv6_deny]))["verdict"], "ALLOWED"
    )
    dual_stack = _verdict(
        _verdict_runner(policies=[ipv6_deny], stack_type="IPV4_IPV6")
    )
    self.assertEqual(dual_stack["verdict"], "INDETERMINATE")
    self.assertIsNone(dual_stack["ip_version"])
    self.assertIn("IP version is unknown", " ".join(dual_stack["notes"]))
    mismatch = _verdict(
        _verdict_runner(policies=[ipv6_deny]), target_ip="2001:db8::1"
    )
    self.assertEqual(mismatch["verdict"], "DENIED")
    self.assertIn("IPv4-only", " ".join(mismatch["notes"]))

    whole_subnet = _policy(
        "net-pol",
        "NETWORK",
        [_policy_rule(10, "deny", dest=["0.0.0.0/0"], src=["10.8.0.0/16"])],
    )
    self.assertEqual(
        _verdict(_verdict_runner(policies=[whole_subnet]))["verdict"], "DENIED"
    )
    part_subnet = _policy(
        "net-pol",
        "NETWORK",
        [_policy_rule(10, "deny", dest=["0.0.0.0/0"], src=["10.8.0.0/25"])],
    )
    part = _verdict(_verdict_runner(policies=[part_subnet]))
    self.assertEqual(part["verdict"], "INDETERMINATE")
    self.assertIn("partly cover", part["unevaluated_rules"][0]["reasons"][0])
    other_subnet = _policy(
        "net-pol",
        "NETWORK",
        [_policy_rule(10, "deny", dest=["0.0.0.0/0"], src=["10.9.0.0/24"])],
    )
    self.assertEqual(
        _verdict(_verdict_runner(policies=[other_subnet]))["verdict"],
        "ALLOWED",
    )
    scoped = _policy(
        "org-pol",
        "HIERARCHY",
        [
            _policy_rule(
                10,
                "deny",
                dest=["0.0.0.0/0"],
                targetResources=["projects/p/global/networks/other-vpc"],
            ),
            _policy_rule(
                20,
                "deny",
                dest=["0.0.0.0/0"],
                targetServiceAccounts=["etl@p.iam.gserviceaccount.com"],
            ),
        ],
    )
    scoped_verdict = _verdict(_verdict_runner(policies=[scoped]))
    self.assertEqual(scoped_verdict["decided_by"]["priority"], 20)

  def test_range_state_helpers(self):
    remote = spark_env_inspector._remote_ranges_state
    local = spark_env_inspector._local_ranges_state
    ip = spark_env_inspector.ipaddress.ip_address
    net = spark_env_inspector.ipaddress.ip_network
    self.assertEqual(remote(["10.0.0.0/8"], ip("10.1.2.3"), 4), "match")
    self.assertEqual(remote(["10.0.0.0/8"], ip("11.1.2.3"), 4), "no_match")
    self.assertEqual(remote(["bogus"], ip("11.1.2.3"), 4), "unknown")
    self.assertEqual(remote(["0.0.0.0/0"], None, 4), "match")
    self.assertEqual(remote(["0.0.0.0/0"], None, None), "unknown")
    self.assertEqual(remote(["0.0.0.0/0", "::/0"], None, None), "match")
    self.assertEqual(remote(["::/0"], None, 4), "no_match")
    self.assertEqual(remote([], None, None), "no_match")
    self.assertEqual(local(["10.0.0.0/8"], []), "unknown")
    self.assertEqual(local(["10.0.0.0/8"], [net("10.8.0.0/24")]), "match")
    self.assertEqual(local(["bogus"], [net("10.8.0.0/24")]), "unknown")

  def test_cli_flags_json_and_markdown(self):
    hierarchy = _policy(
        "folder-policy",
        "HIERARCHY",
        [
            _policy_rule(31, "goto_next", dest=["0.0.0.0/0"]),
            _policy_rule(38, "deny", dest=["0.0.0.0/0"]),
        ],
    )
    runner = _verdict_runner(
        policies=[hierarchy],
        vpc_rules=[
            _vpc_rule(
                "deny-db",
                900,
                destinationRanges=["10.50.0.0/16"],
                denied=[{"IPProtocol": "tcp"}],
            )
        ],
    )
    base = [
        "--project=p",
        "--region=us-central1",
        "--batch_id=b-fw",
        "--action=network",
    ]
    for bad in (
        ["--target_ip=10.0.0.1"],
        ["--target_port=443", "--target_ip=x"],
    ):
      with contextlib.redirect_stderr(io.StringIO()):
        with self.assertRaises(SystemExit, msg=bad):
          spark_env_inspector.main(base + bad, runner=runner)

    code, stdout, _ = _run_cli(base + ["--format=json"], runner)
    self.assertEqual(code, 0)
    self.assertIsNone(json.loads(stdout)["firewall_verdict"])
    code, stdout, _ = _run_cli(base, runner)
    self.assertEqual(code, 0)
    self.assertIn("Re-run with `--target_port=<PORT>`", stdout)
    self.assertNotIn("## Firewall Verdict", stdout)

    code, stdout, _ = _run_cli(base + ["--target_port=443"], runner)
    self.assertEqual(code, 0)
    self.assertNotIn("Re-run with `--target_port=<PORT>`", stdout)
    verdict_md = stdout.split("## Firewall Verdict", 1)[1].split("\n\n", 1)[0]
    self.assertEqual(
        "## Firewall Verdict" + verdict_md,
        "\n".join([
            "## Firewall Verdict (`EGRESS tcp:443` to `any IPv4 address`)",
            "- verdict: `INDETERMINATE` (possible outcomes: ALLOWED, DENIED)",
            (
                "- evaluation order: hierarchical policy `folder-policy` ->"
                " VPC firewall rules -> implied rules"
            ),
            (
                "- hierarchical policy `folder-policy`: first match"
                " priority=`31` `goto_next` dest=['0.0.0.0/0']"
            ),
            (
                "- VPC firewall rules: first match priority=`900` `deny`"
                " `deny-db` dest=['10.50.0.0/16'] (indeterminate)"
            ),
            (
                "- implied rules: first match priority=`65535` `allow`"
                " `implied allow egress`"
            ),
            "- unevaluated rules (check by hand):",
            (
                "  - VPC firewall rules priority=`900` `deny` `deny-db`:"
                " matches only some destination addresses; pass --target_ip"
                " to evaluate it"
            ),
        ]),
    )
    code, stdout, _ = _run_cli(
        base + ["--target_port=443", "--target_ip=10.50.0.9"], runner
    )
    self.assertEqual(code, 0)
    self.assertIn(
        "- verdict: `DENIED`, decided by VPC firewall rules priority=`900`"
        " `deny` `deny-db`",
        stdout,
    )


if __name__ == "__main__":
  unittest.main()
