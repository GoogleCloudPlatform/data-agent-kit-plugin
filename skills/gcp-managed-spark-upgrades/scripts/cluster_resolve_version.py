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
# requires-python = ">=3.10"
# dependencies = []
# ///

"""Resolves the latest suitable Dataproc version from public release notes."""

import argparse
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from typing import Any


class VersionPageParser(HTMLParser):
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


def get_candidates(version_track: str, image_type: str) -> list[str]:
    """Fetches candidate versions for a given track and image type.

    Args:
        version_track: The major.minor version track (e.g., "2.2").
        image_type: The image type ("serverless" or "gce").

    Returns:
        A list of candidate version strings.
    """
    if image_type == "serverless":
        url = f"https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-{version_track}"
    else:
        url = f"https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-release-{version_track}"

    try:
        with urllib.request.urlopen(url) as response:
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
            with urllib.request.urlopen(url) as response:
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve latest suitable Dataproc version (OSS version)."
    )
    parser.add_argument(
        "--version", required=True, help="Major.Minor version, e.g., 2.2"
    )
    parser.add_argument(
        "--type",
        choices=["gce", "serverless"],
        default="gce",
        help="Image type",
    )
    parser.add_argument("--distro", help="Distro for GCE, e.g., debian12, rocky9")
    parser.add_argument(
        "--raw", action="store_true", help="Only output the version string"
    )

    args = parser.parse_args()

    target_version = args.version
    image_type = args.type
    distro_filter = args.distro
    raw_output = args.raw

    # Fetch candidates and rollbacks from public docs
    if not raw_output:
        print("Fetching data from public docs...", file=sys.stderr)

    candidates = get_candidates(target_version, image_type)
    rolled_back = get_rolled_back_versions()

    if not candidates:
        if not raw_output:
            print(
                f"No candidates found for track {target_version} ({image_type})",
                file=sys.stderr,
            )
        sys.exit(1)

    # Filter candidates
    suitable_candidates = []
    for c in candidates:
        # Check if full version is rolled back
        if c in rolled_back:
            continue
        # Check if base version is rolled back (for GCE, e.g. "2.2.82" rolls back "2.2.82-debian12")
        base_version = c.split("-")[0]
        if base_version in rolled_back:
            continue

        if image_type == "gce":
            distro = extract_distro(c)
            if distro_filter and distro != distro_filter:
                continue

        suitable_candidates.append(c)

    if not suitable_candidates:
        if not raw_output:
            print(
                f"No suitable version found for {target_version} ({image_type})"
                " after filtering rollbacks.",
                file=sys.stderr,
            )
        sys.exit(1)

    # Sort
    suitable_candidates.sort(key=sort_key, reverse=True)

    latest_version = suitable_candidates[0]

    if raw_output:
        print(latest_version)
    else:
        print(f"Latest suitable version: {latest_version}")

        if image_type == "gce" and not distro_filter:
            # Group by distro
            latest_per_distro = {}
            for v in suitable_candidates:
                d = extract_distro(v)
                if d and d not in latest_per_distro:
                    latest_per_distro[d] = v

            print("\nLatest per distro:")
            for d, v in latest_per_distro.items():
                print(f"  {d}: {v}")

        if len(suitable_candidates) > 1:
            print("\nOther suitable candidates (in descending order):")
            for v in suitable_candidates[1:5]:
                print(f"  {v}")


if __name__ == "__main__":
    main()
