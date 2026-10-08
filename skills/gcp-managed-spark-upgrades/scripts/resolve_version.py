# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///

"""Resolves the Managed Spark (formerly Dataproc) version to use as an upgrade target.

Cluster: resolves a <major>.<minor> track to the newest full image version
(<major>.<minor>.<sub-minor>-<distro>) that has not been rolled back, using the
public version and release-notes pages.

Serverless: runtime versions are <major>.<minor> only. Batches always run the
newest sub-minor release of their runtime and a sub-minor cannot be pinned, so
nothing is resolved: the script confirms that the runtime's documentation page
lists releases and prints <major>.<minor>.

The version to use is printed alone on stdout; notes go to stderr.
"""

from __future__ import annotations

import argparse
import html.parser
import re
import sys
from typing import Callable
import urllib.request

_CLUSTER_PAGE = (
    "https://cloud.google.com/dataproc/docs/concepts/versioning/"
    "dataproc-release-{track}"
)
_SERVERLESS_PAGE = (
    "https://cloud.google.com/dataproc-serverless/docs/concepts/versions/"
    "spark-runtime-{track}"
)
_SERVERLESS_VERSIONS_PAGE = (
    "https://cloud.google.com/dataproc-serverless/docs/concepts/versions/"
    "spark-runtime-versions"
)
_FETCH_TIMEOUT_SECONDS = 30


class VersionPageParser(html.parser.HTMLParser):
  """Parser to extract table headers from Dataproc release documentation."""

  def __init__(self) -> None:
    super().__init__()
    self.in_table: bool = False
    self.in_tr: bool = False
    self.in_th: bool = False
    self.current_th_text: list[str] = []
    self.headers: list[str] = []
    self.table_row_count: int = 0

  def handle_starttag(
      self, tag: str, attrs: list[tuple[str, str | None]]
  ) -> None:
    if tag == "table":
      self.in_table = True
      self.table_row_count = 0
    elif tag == "tr" and self.in_table:
      self.in_tr = True
      self.table_row_count += 1
    elif tag == "th" and self.in_tr and self.table_row_count == 1:
      self.in_th = True
      self.current_th_text = []

  def handle_endtag(self, tag: str) -> None:
    if tag == "table":
      self.in_table = False
    elif tag == "tr":
      self.in_tr = False
    elif tag == "th" and self.in_th:
      self.in_th = False
      self.headers.append("".join(self.current_th_text).strip())

  def handle_data(self, data: str) -> None:
    if self.in_th:
      self.current_th_text.append(data)


def is_valid_version_string(s: str) -> bool:
    """Checks if a string is a valid Dataproc version format."""
    return re.fullmatch(r"\d+\.\d+\.\d+(?:-[\w-]+)?", s) is not None


def clean_html(html: str) -> str:
    """Removes HTML tags and normalizes newlines."""
    html = re.sub(r"</?(p|div|li|tr|h\d|ul|ol)\b[^>]*>", "\n", html)
    html = re.sub(r"<[^>]*>", "", html)
    html = re.sub(r"\n+", "\n", html)
    return html


def _parse_gce_header(header: str) -> list[str]:
  """Parses a GCE header string into individual version-distro candidates.

  Example: "2.2.84-debian12/rocky9" -> ["2.2.84-debian12", "2.2.84-rocky9"]
  """
  match = re.fullmatch(r"([\d.]+)-(.*)", header)
  if not match:
    return []

  version = match.group(1)
  rest = match.group(2)
  # Remove date suffix if present (e.g. "2026/06/22")
  rest_no_date = re.sub(r"\d{4}/\d{2}/\d{2}$", "", rest)

  parts = rest_no_date.split("/")
  candidates = []
  for p in parts:
    distro = p.strip("-")
    if distro:
      candidates.append(f"{version}-{distro}")
  return candidates


def version_page_url(version_track: str, image_type: str) -> str:
  """Returns the documentation page that lists the releases of a track."""
  template = _SERVERLESS_PAGE if image_type == "serverless" else _CLUSTER_PAGE
  return template.format(track=version_track)


def get_candidates(version_track: str, image_type: str) -> list[str]:
  """Fetches candidate versions for a given track and image type.

  Args:
      version_track: The major.minor version track (e.g., "2.2").
      image_type: The image type ("serverless" or "cluster").

  Returns:
      A list of candidate version strings.
  """
  url = version_page_url(version_track, image_type)

  try:
    with urllib.request.urlopen(
        url, timeout=_FETCH_TIMEOUT_SECONDS
    ) as response:
      html_content = response.read().decode("utf-8")
  except Exception as e:
    print(f"Error fetching {url}: {e}", file=sys.stderr)
    return []

  parser = VersionPageParser()
  parser.feed(html_content)

  candidates = []
  for header in parser.headers:
    header_clean = re.sub(r"\s+", "", header)

    if image_type == "serverless":
      header_no_date = re.sub(r"\d{4}/\d{2}/\d{2}$", "", header_clean)
      if re.fullmatch(r"\d+\.\d+\.\d+", header_no_date):
        candidates.append(header_no_date)
    else:
      candidates.extend(_parse_gce_header(header_clean))

  return candidates


def get_rolled_back_versions() -> set[str]:
  """Fetches and parses Dataproc release notes to find rolled back versions.

  Returns:
      A set of version strings that have been rolled back.
  """
  urls = [
      "https://cloud.google.com/dataproc/docs/release-notes",
      "https://cloud.google.com/dataproc-serverless/docs/release-notes",
  ]
  rolled_back = set()

  for url in urls:
    try:
      with urllib.request.urlopen(
          url, timeout=_FETCH_TIMEOUT_SECONDS
      ) as response:
        html_content = response.read().decode("utf-8")
    except Exception as e:
      print(f"Warning: Error fetching {url}: {e}", file=sys.stderr)
      continue

    sections = re.split(r"<h2\b", html_content)
    for section in sections:
      if "rolled back" not in section.lower():
        continue

      cleaned_section = clean_html(section)

      # Look for patterns like "rolled back: 2.2.84, 2.2.85"
      matches = re.findall(
          r"rolled[\s_-]back.*?:(.*?)(?=\n[A-Z]|\n\n|$)",
          cleaned_section,
          re.DOTALL | re.IGNORECASE,
      )
      for match in matches:
        parts = re.split(r"[,\s]+", match.strip())
        for p in parts:
          p_clean = p.strip()
          if is_valid_version_string(p_clean):
            rolled_back.add(p_clean)

      # Look for patterns like "Rollback Notice: ... The 2.2.84 image versions were rolled back"
      matches2 = re.findall(
          r"Rollback Notice:.*?The\s*([\d.]+)\s*image versions were"
          r" rolled back",
          cleaned_section,
          re.DOTALL | re.IGNORECASE,
      )
      for match in matches2:
        match_clean = match.strip()
        if is_valid_version_string(match_clean):
          rolled_back.add(match_clean)

  return rolled_back


def parse_version(version_str: str) -> tuple[int, int, int, int]:
    """Parses a version string into a tuple for sorting."""
    match = re.fullmatch(
        r"(\d+)\.(\d+)\.(\d+)(?:-RC(\d+))?(?:-.*)?", version_str
    )
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        rc = int(match.group(4)) if match.group(4) else 999
        return (major, minor, patch, rc)
    return (0, 0, 0, 0)


def extract_distro(version_str: str) -> str:
    """Extracts the distribution name from a version string."""
    match = re.fullmatch(r"\d+\.\d+\.\d+(?:-RC\d+)?-(.*)", version_str)
    if match:
        return match.group(1)
    return ""


def get_distro_priority(distro: str) -> int:
    """Returns a priority for sorting distributions (higher is preferred)."""
    if distro.startswith("debian"):
        return 4
    elif distro.startswith("ubuntu"):
        return 3
    elif distro.startswith("rocky"):
        return 2
    elif distro.startswith("centos"):
        return 1
    return 0


def sort_key(candidate: str) -> tuple[tuple[int, int, int, int], int]:
  """Key function for sorting version candidates."""
  version_str = candidate
  parsed_version = parse_version(version_str)
  distro = extract_distro(version_str)
  priority = get_distro_priority(distro)
  return (parsed_version, priority)


def parse_requested_version(version: str) -> tuple[str, str | None, str | None]:
  """Splits a requested version into (track, sub_minor, distro).

  Examples: "2.2" -> ("2.2", None, None); "2.2-debian12" -> ("2.2", None,
  "debian12"); "2.2.45" -> ("2.2", "45", None).

  Raises:
      ValueError: If the version does not start with <major>.<minor>.
  """
  match = re.fullmatch(
      r"(\d+\.\d+)(?:\.(\d+))?(?:-([A-Za-z][\w-]*))?", version.strip()
  )
  if not match:
    raise ValueError(
        f"'{version}' is not a version like 2.2, 2.2-debian12, or 2.2.45."
    )
  return match.group(1), match.group(2), match.group(3)


def matches_distro(candidate_distro: str, distro_filter: str) -> bool:
  """Matches a distro exactly, or by OS family when the filter has no digits.

  Example: "ubuntu" matches "ubuntu22"; "ubuntu22" matches only "ubuntu22".
  """
  if distro_filter.isalpha():
    return candidate_distro.startswith(distro_filter)
  return candidate_distro == distro_filter


def resolve_serverless(
    requested: str,
    track: str,
    sub_minor: str | None,
    distro: str | None,
    note: Callable[[str], None],
) -> int:
  """Confirms that a Serverless runtime exists and prints <major>.<minor>.

  Serverless batches always run the newest sub-minor release of a runtime, so
  there is no sub-minor to resolve or pin.

  Returns:
      The process exit code.
  """
  if distro:
    print(
        f"Error: '{requested}' looks like a cluster image version."
        " Serverless runtime versions are <major>.<minor> (e.g."
        f" {track}); confirm the deployment type.",
        file=sys.stderr,
    )
    return 2
  if sub_minor:
    note(f"Serverless can't pin a sub-minor version; using runtime {track}.")

  note("Fetching data from public docs...")
  url = version_page_url(track, "serverless")
  if not get_candidates(track, "serverless"):
    print(
        f"Error: no releases found for Serverless runtime {track} at"
        f" {url}. Check the supported runtimes at"
        f" {_SERVERLESS_VERSIONS_PAGE}.",
        file=sys.stderr,
    )
    return 1

  print(track)
  note(
      f"Pass --version={track} to 'gcloud dataproc batches submit'."
      f" Serverless always runs the newest release of runtime {track}."
  )
  note(f"Component versions: newest release column at {url}")
  return 0


def resolve_cluster(
    requested: str,
    track: str,
    sub_minor: str | None,
    distro_filter: str | None,
    note: Callable[[str], None],
) -> int:
  """Prints the newest full image version of a track that wasn't rolled back.

  Returns:
      The process exit code.
  """
  if sub_minor:
    rolled_back = get_rolled_back_versions()
    base_version = f"{track}.{sub_minor}"
    if requested in rolled_back or base_version in rolled_back:
      print(
          f"Error: '{requested}' ({base_version}) was rolled back."
          f" Run with --version={track} to resolve a non-rolled-back"
          " sub-minor version.",
          file=sys.stderr,
      )
      return 1
    print(
        f"Error: '{requested}' already includes a sub-minor version; use"
        " it as is.",
        file=sys.stderr,
    )
    return 2

  note("Fetching data from public docs...")
  url = version_page_url(track, "cluster")
  candidates = get_candidates(track, "cluster")
  if not candidates:
    print(
        f"Error: no image versions found for track {track} at {url}.",
        file=sys.stderr,
    )
    return 1

  rolled_back = get_rolled_back_versions()

  # Filter candidates
  suitable_candidates = []
  for c in candidates:
    # Check if full version is rolled back
    if c in rolled_back:
      continue
    # Check if base version is rolled back (e.g. "2.2.82" rolls back "2.2.82-debian12")
    base_version = c.split("-")[0]
    if base_version in rolled_back:
      continue
    if distro_filter and not matches_distro(extract_distro(c), distro_filter):
      continue
    suitable_candidates.append(c)

  if not suitable_candidates:
    distro_text = f" and distro '{distro_filter}'" if distro_filter else ""
    print(
        f"Error: no suitable image version for track {track}{distro_text}"
        " after filtering rolled-back versions.",
        file=sys.stderr,
    )
    return 1

  suitable_candidates.sort(key=sort_key, reverse=True)
  print(suitable_candidates[0])

  if not distro_filter:
    note(
        "No --distro given: picked by distro preference (debian > ubuntu"
        " > rocky). Pass --distro=<family> to keep the source's OS family."
    )
    latest_per_distro = {}
    for v in suitable_candidates:
      d = extract_distro(v)
      if d and d not in latest_per_distro:
        latest_per_distro[d] = v
    note("Latest per distro:")
    for d, v in latest_per_distro.items():
      note(f"  {d}: {v}")

  if len(suitable_candidates) > 1:
    note("Other suitable candidates (in descending order):")
    for v in suitable_candidates[1:5]:
      note(f"  {v}")
  note(f"Component versions: column {suitable_candidates[0]} at {url}")
  return 0


def main() -> int:
  parser = argparse.ArgumentParser(
      description=(
          "Resolve the Managed Spark (Dataproc) version to use as an upgrade"
          " target. Prints the version alone on stdout; notes go to stderr."
      )
  )
  parser.add_argument(
      "--type",
      required=True,
      choices=["cluster", "serverless"],
      help=(
          "Deployment type: 'cluster' (image versions) or 'serverless'"
          " (runtime versions, <major>.<minor> only)."
      ),
  )
  parser.add_argument(
      "--version",
      required=True,
      help="Target track, e.g. 2.2 (clusters also accept 2.2-debian12).",
  )
  parser.add_argument(
      "--distro",
      help="Cluster only: a distro (e.g. debian12) or OS family (e.g. ubuntu).",
  )
  parser.add_argument(
      "--raw",
      action="store_true",
      help="Print only the version; suppress the notes on stderr.",
  )
  args = parser.parse_args()

  def note(message: str) -> None:
    if not args.raw:
      print(message, file=sys.stderr)

  try:
    track, sub_minor, version_distro = parse_requested_version(args.version)
  except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 2

  if args.type == "serverless":
    if args.distro:
      print(
          "Error: --distro applies only to --type=cluster.",
          file=sys.stderr,
      )
      return 2
    return resolve_serverless(
        args.version, track, sub_minor, version_distro, note
    )

  if version_distro and args.distro and version_distro != args.distro:
    print(
        f"Error: --version={args.version} and --distro={args.distro} name"
        " different distros.",
        file=sys.stderr,
    )
    return 2
  return resolve_cluster(
      args.version, track, sub_minor, args.distro or version_distro, note
  )


if __name__ == "__main__":
  sys.exit(main())
