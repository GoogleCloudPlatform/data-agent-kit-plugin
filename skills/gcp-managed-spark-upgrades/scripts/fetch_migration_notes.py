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
# requires-python = ">=3.9"
# dependencies = []
# ///

"""Fetches the official Apache Spark migration notes between two Spark versions.

Downloads the Spark SQL, Core, PySpark, MLlib, and Structured Streaming
migration guides from the Apache Spark repository at the target version's
release tag (or its release branch) and keeps only the "Upgrading from X to Y"
sections where source < Y <= target (plus PySpark's Koalas migration guide when
upgrading across Spark 3.2). A guide that doesn't exist at that ref (e.g. the
consolidated PySpark guide before Spark 3.4) is read from master instead; the
version filter keeps only the sections that apply.

Writes one Markdown file per guide that has such sections to the output
directory, plus index.md, which is also printed on stdout: the sections and
notes per guide, the Java, Scala, and Python versions that the source and
target Spark versions support (from docs/index.md), and the target's minimum
PySpark dependency versions (from PySpark's setup.py). The files of an earlier
run in the same directory are deleted first, so none of them can be mistaken
for the current notes.

The script needs only the Python standard library, as its inline script
metadata (PEP 723) declares: run it with `uv run` or `python3`.

Exit codes: 0 when every guide was downloaded, 1 when a guide download failed
or a guide was not found, and 2 for invalid arguments or a target version
without a release tag or branch.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import gzip
import http.client
import os
import re
import sys
import time
from typing import Optional, Sequence, Tuple
import urllib.error
import urllib.request
import zlib

_RAW_URL = "https://raw.githubusercontent.com/apache/spark/{ref}/{path}"
_DOCS_URL = "https://spark.apache.org/docs/{version}/migration-guide.html"
# spark.apache.org serves only current releases; older ones are archived here.
_ARCHIVED_DOCS_URL = "https://archive.apache.org/dist/spark/docs/{version}"
_INDEX_PATH = "docs/index.md"
_INDEX_FILE = "index.md"
_INDEX_HEADER = "Spark migration notes "
_FETCH_TIMEOUT_SECONDS = 30
_FETCH_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 1.0
_MAX_RETRY_DELAY_SECONDS = 10.0
# Rate limiting and server errors are transient; other HTTP errors aren't.
_RETRIABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})
_MAX_PARALLEL_FETCHES = 8

# The start of the next section: a Markdown "## " heading, or a
# reStructuredText title (a line followed by an unindented underline).
_MD_BOUNDARY = re.compile(r"^## ", re.MULTILINE)
_RST_BOUNDARY = re.compile(
    r"(?:^[-=]{3,}[ \t]*\n)?^(?![-=~^]{3,}[ \t]*$)[^\n]+\n[-=]{3,}[ \t]*$",
    re.MULTILINE,
)
_VERSION_GROUP = r"(\d+(?:\.\d+)*)"

Version = Tuple[int, ...]


def _heading(pattern: str) -> re.Pattern[str]:
  """Compiles a section heading pattern; group 2 is the version upgraded to."""
  # Older guides (e.g. Spark 2.4's SQL guide) write "Upgrading From".
  return re.compile(pattern, re.MULTILINE | re.IGNORECASE)


@dataclasses.dataclass(frozen=True)
class Guide:
  """A migration guide in the Apache Spark repository."""

  key: str
  title: str
  paths: Tuple[str, ...]
  heading: re.Pattern[str]
  boundary: re.Pattern[str]


GUIDES = (
    Guide(
        key="sql",
        title="Spark SQL",
        # Spark 2.4 keeps the notes on a separate "upgrade" page.
        paths=(
            "docs/sql-migration-guide.md",
            "docs/sql-migration-guide-upgrade.md",
        ),
        heading=_heading(
            rf"^## Upgrading from Spark SQL (\S+) to {_VERSION_GROUP}[^\n]*"
        ),
        boundary=_MD_BOUNDARY,
    ),
    Guide(
        key="core",
        title="Spark Core",
        paths=("docs/core-migration-guide.md",),
        heading=_heading(
            rf"^## Upgrading from Core (\S+) to {_VERSION_GROUP}[^\n]*"
        ),
        boundary=_MD_BOUNDARY,
    ),
    Guide(
        key="pyspark",
        title="PySpark",
        paths=("python/docs/source/migration_guide/pyspark_upgrade.rst",),
        heading=_heading(
            rf"^Upgrading from PySpark (\S+) to {_VERSION_GROUP}[^\n]*\n"
            r"-{3,}[ \t]*$"
        ),
        boundary=_RST_BOUNDARY,
    ),
    Guide(
        key="mllib",
        title="MLlib",
        paths=("docs/ml-migration-guide.md",),
        heading=_heading(
            rf"^## Upgrading from MLlib (\S+) to {_VERSION_GROUP}[^\n]*"
        ),
        boundary=_MD_BOUNDARY,
    ),
    Guide(
        key="structured_streaming",
        title="Structured Streaming",
        # The guide moved to docs/streaming/ in Spark 4.0, where the old path
        # holds only a redirect.
        paths=(
            "docs/streaming/ss-migration-guide.md",
            "docs/ss-migration-guide.md",
        ),
        heading=_heading(
            rf"^## Upgrading from Structured Streaming (\S+) to "
            rf"{_VERSION_GROUP}[^\n]*"
        ),
        boundary=_MD_BOUNDARY,
    ),
)

_KOALAS_PATH = "python/docs/source/migration_guide/koalas_to_pyspark.rst"
_KOALAS_VERSION: Version = (3, 2)
_KOALAS_HEADING = _heading(
    r"^(?:={3,}[ \t]*\n)?(Migrating from Koalas to pandas API on Spark)"
    r"[ \t]*\n={3,}[ \t]*$"
)
_SETUP_PATHS = ("python/packaging/classic/setup.py", "python/setup.py")
_MINIMUM_PACKAGES = (
    ("pandas", "pandas"),
    ("numpy", "NumPy"),
    ("pyarrow", "PyArrow"),
)


class FetchError(Exception):
  """A download failed for a reason other than the file not existing."""


@dataclasses.dataclass
class GuideResult:
  """The sections of one guide that apply to the upgrade."""

  guide: Guide
  ref: Optional[str] = None
  url: Optional[str] = None
  sections: list[tuple[str, str]] = dataclasses.field(default_factory=list)
  error: Optional[str] = None
  output_path: Optional[str] = None


def parse_version(text: str) -> Version:
  """Parses a Spark version such as 3.5 or 3.5.3.

  Args:
      text: The Spark version string to parse.

  Returns:
      The parsed version tuple of integers.

  Raises:
      ValueError: If the text isn't <major>.<minor>[.<patch>].
  """
  match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?", text.strip())
  if not match:
    raise ValueError(f"'{text}' is not a Spark version like 3.5 or 3.5.3.")
  return tuple(int(part) for part in match.groups() if part is not None)


def _lower_bound(version: Sequence[int]) -> Version:
  """3.5 -> (3, 5, 0): a version without a patch counts as its first release."""
  return (tuple(version) + (0, 0, 0))[:3]


def _upper_bound(version: Sequence[int]) -> Version:
  """3.5 -> (3, 5, maxsize): a version without a patch covers all releases."""
  return (tuple(version) + (sys.maxsize, sys.maxsize))[:3]


def in_range(
    section_to: Sequence[int], source: Sequence[int], target: Sequence[int]
) -> bool:
  """Whether a section that upgrades *to* section_to applies to the upgrade.

  A source without a patch version counts as its .0 release, so the patch
  sections of its minor version are included; a target without a patch version
  includes all of its patch releases.

  Args:
      section_to: The version that the migration section upgrades to.
      source: The source Spark version.
      target: The target Spark version.

  Returns:
      True if source < section_to <= target.
  """
  return _lower_bound(source) < _lower_bound(section_to) <= _upper_bound(target)


def release_refs(version: Sequence[int]) -> list[str]:
  """Git refs for a version: its release tag (with a patch), then its branch."""
  refs = []
  if len(version) == 3:
    refs.append("v{}.{}.{}".format(*version))
  refs.append("branch-{}.{}".format(*version[:2]))
  return refs


def fetch_text(ref: str, path: str) -> Optional[str]:
  """Returns a file from the Apache Spark repository, or None if it's missing.

  Asks for a gzip-compressed response, and retries rate limiting, server
  errors, and network errors with exponential backoff (or the server's
  Retry-After delay, up to _MAX_RETRY_DELAY_SECONDS).

  Args:
      ref: The Git tag or branch name in apache/spark.
      path: The repository-relative file path.

  Returns:
      The UTF-8 text of the file, or None on HTTP 404.

  Raises:
      FetchError: If the download still fails after the last attempt, or fails
        with an HTTP error other than 404 that retrying doesn't fix.
  """
  url = _RAW_URL.format(ref=ref, path=path)
  request = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
  error = ""
  delay = _RETRY_DELAY_SECONDS
  for attempt in range(_FETCH_ATTEMPTS):
    if attempt:
      time.sleep(min(delay, _MAX_RETRY_DELAY_SECONDS))
      delay *= 2
    try:
      with urllib.request.urlopen(
          request, timeout=_FETCH_TIMEOUT_SECONDS
      ) as response:
        data = response.read()
        if response.headers.get("Content-Encoding", "").lower() == "gzip":
          data = gzip.decompress(data)
      return data.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
      e.close()
      if e.code == 404:
        return None
      error = f"HTTP {e.code}"
      if e.code not in _RETRIABLE_HTTP_CODES:
        break
      retry_after = (e.headers or {}).get("Retry-After", "").strip()
      if retry_after.isdigit():
        delay = max(delay, float(retry_after))
    # URLError, timeouts, dropped connections, and truncated gzip data.
    except (OSError, EOFError, http.client.HTTPException, zlib.error) as e:
      error = str(e) or type(e).__name__
  raise FetchError(f"{url}: {error}")


def extract_sections(
    text: str, guide: Guide, source: Sequence[int], target: Sequence[int]
) -> list[tuple[str, str]]:
  """Returns (title, body) of each section in range, in document order."""
  boundaries = [m.start() for m in guide.boundary.finditer(text)]
  sections = []
  for match in guide.heading.finditer(text):
    section_to = tuple(int(part) for part in match.group(2).split("."))
    if not in_range(section_to, source, target):
      continue
    end = next((b for b in boundaries if b >= match.end()), len(text))
    title = match.group(0).splitlines()[0].lstrip("#").strip()
    sections.append((title, text[match.end() : end].strip("\n")))
  return sections


def _fetch_koalas_section(refs: Sequence[str]) -> Optional[tuple[str, str]]:
  """Returns the (title, body) of koalas_to_pyspark.rst from the first ref."""
  for ref in refs:
    text = fetch_text(ref, _KOALAS_PATH)
    if text is None:
      continue
    match = _KOALAS_HEADING.search(text)
    if match:
      return match.group(1).strip(), text[match.end() :].strip("\n")
  return None


def fetch_guide(
    guide: Guide,
    refs: Sequence[str],
    source: Sequence[int],
    target: Sequence[int],
) -> GuideResult:
  """Reads a guide from the first ref and path that has migration sections.

  A file without any migration section heading (missing, an index page, or a
  redirect) is skipped. A download error stops the search and is recorded in
  the result.

  Args:
      guide: The guide definition to fetch.
      refs: Candidate Git refs to try in order.
      source: The source Spark version.
      target: The target Spark version.

  Returns:
      The GuideResult with extracted sections or error details.
  """
  result = GuideResult(guide)
  for ref in refs:
    for path in guide.paths:
      try:
        text = fetch_text(ref, path)
      except FetchError as e:
        result.error = str(e)
        return result
      if text is None or not guide.heading.search(text):
        continue
      result.ref = ref
      result.url = _RAW_URL.format(ref=ref, path=path)
      result.sections = extract_sections(text, guide, source, target)
      if guide.key == "pyspark" and in_range(_KOALAS_VERSION, source, target):
        try:
          koalas = _fetch_koalas_section(refs)
        except FetchError as e:
          result.ref = None
          result.url = None
          result.sections = []
          result.error = str(e)
          return result
        if koalas:
          result.sections.append(koalas)
      return result
  return result


def resolve_ref(refs: Sequence[str]) -> Tuple[Optional[str], Optional[str]]:
  """Returns (the first ref that exists, its docs/index.md), or (None, None).

  Every Spark release has docs/index.md, so it tells which refs exist.

  Args:
      refs: Candidate Git refs to probe in order.

  Returns:
      A tuple of (resolved_ref, index_text), or (None, None) if none exist.

  Raises:
      FetchError: If a download fails.
  """
  for ref in refs:
    text = fetch_text(ref, _INDEX_PATH)
    if text is not None:
      return ref, text
  return None, None


def runtime_requirements(index_text: Optional[str]) -> Optional[str]:
  """Returns the "Spark runs on Java ..." sentence of docs/index.md."""
  match = re.search(
      r"^.*Spark runs on Java[^\n]*", index_text or "", re.MULTILINE
  )
  if not match:
    return None
  # Spark 2.x appends a templated sentence ("For the Scala API, Spark
  # {{site.SPARK_VERSION}} uses ..."); keep only the runtime list and mark
  # Scala unavailable when docs/index.md omits a concrete Scala version.
  line = re.split(r"\s+For the Scala API", match.group(0))[0].strip()
  if "Scala" not in line:
    return f"{line} (Scala: unavailable)"
  return line


def pyspark_minimums(
    refs: Sequence[str],
) -> Tuple[Optional[str], dict[str, str]]:
  """Returns (where, version specifiers) from PySpark's setup.py at a ref.

  Every value is a specifier such as ">=2.2.0" or ">=1.15,<2", so that upper
  bounds stand out.

  Args:
      refs: Candidate Git refs to inspect for PySpark's setup.py.

  Returns:
      A tuple of ("<path> at <ref>", package_to_specifier_dict), or (None, {}).
  """
  for ref in refs:
    for path in _SETUP_PATHS:
      try:
        text = fetch_text(ref, path)
      except FetchError:
        return None, {}
      if not text:
        continue
      found = {}
      match = re.search(r"python_requires\s*=\s*['\"]([^'\"]+)['\"]", text)
      if match:
        found["Python"] = match.group(1)
      for package, label in _MINIMUM_PACKAGES:
        match = re.search(
            rf"^_minimum_{package}_version\s*=\s*['\"]([^'\"]+)['\"]",
            text,
            re.MULTILINE,
        )
        if match:
          found[label] = ">=" + match.group(1)
      if "NumPy" not in found:
        # Spark 3.x declares NumPy only in its extras, e.g. "numpy>=1.15,<2".
        match = re.search(r"['\"]numpy\s*([<>=!~][^'\"]*)['\"]", text)
        if match:
          found["NumPy"] = match.group(1).strip()
      if found:
        return f"{path} at {ref}", found
  return None, {}


def count_notes(body: str) -> int:
  """Counts the list items of a section (approximately one per note)."""
  return len(re.findall(r"^ {0,3}[-*] ", body, re.MULTILINE))


def _output_files(out_dir: str) -> list[str]:
  """The files that the script writes to an output directory."""
  names = [guide.key + ".md" for guide in GUIDES] + [_INDEX_FILE]
  return [os.path.join(out_dir, name) for name in names]


def _written_by_this_script(path: str) -> bool:
  """Whether a file starts with a header that this script writes."""
  try:
    with open(path, encoding="utf-8", errors="replace") as f:
      first_line = f.readline()
  except OSError:
    return False
  headers = [_INDEX_HEADER] + [
      f"# {guide.title} migration notes: " for guide in GUIDES
  ]
  return first_line.startswith(tuple(headers))


def clear_output(out_dir: str) -> list[str]:
  """Deletes the files that an earlier run wrote to an output directory.

  Args:
      out_dir: The output directory to inspect and clean.

  Returns:
      The paths of the files that the script would write but that hold other
      content; they are kept, and no files are deleted when any are present.
  """
  removable = []
  others = []
  for path in _output_files(out_dir):
    if not os.path.lexists(path):
      continue
    if (
        not os.path.islink(path)
        and os.path.isfile(path)
        and _written_by_this_script(path)
    ):
      removable.append(path)
    else:
      others.append(path)
  if not others:
    for path in removable:
      os.remove(path)
  return others


def write_guide(
    result: GuideResult, path: str, source_text: str, target_text: str
) -> None:
  """Writes the sections of a guide to a Markdown file."""
  lines = [
      f"# {result.guide.title} migration notes: {source_text} -> {target_text}",
      "",
      f"Source: {result.url}",
      "",
  ]
  for title, body in result.sections:
    lines += [f"## {title}", "", body, ""]
  with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))


def _plural(count: int, noun: str) -> str:
  return f"{count} {noun}" + ("" if count == 1 else "s")


def _describe(result: GuideResult) -> str:
  key = result.guide.key
  if result.error:
    return f"  {key}: NOT FETCHED ({result.error})"
  if result.ref is None:
    return f"  {key}: not found"
  if not result.sections:
    return f"  {key}: no sections in range (read from {result.ref})"
  notes = sum(count_notes(body) for _, body in result.sections)
  return (
      f"  {key}: {_plural(len(result.sections), 'section')}, about"
      f" {_plural(notes, 'note')}, read from {result.ref} ->"
      f" {result.output_path}"
  )


def _runtime_line(
    label: str, ref: Optional[str], index_text: Optional[str]
) -> str:
  requirements = runtime_requirements(index_text)
  if not requirements:
    return f"  Spark {label}: unavailable"
  return f"  Spark {label} ({ref}): {requirements}"


def _published_guides(target: Sequence[int]) -> str:
  """Where to read the migration guides when they can't be downloaded."""
  if len(target) == 3:
    version = "{}.{}.{}".format(*target)
    return (
        f"{_DOCS_URL.format(version=version)} (archived releases:"
        f" {_ARCHIVED_DOCS_URL.format(version=version)})"
    )
  # The site has pages only for patch releases, and the latest guides keep the
  # sections of all earlier releases.
  minor = "{}.{}".format(*target[:2])
  return (
      f"{_DOCS_URL.format(version='latest')} (keep the sections up to Spark"
      f" {minor})"
  )


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
      description=(
          "Fetch the Apache Spark migration notes between two Spark versions"
          " and write one file per guide. Prints an index on stdout."
      )
  )
  parser.add_argument(
      "--from",
      dest="source",
      required=True,
      help="Source Spark version, e.g. 3.5 or 3.5.3.",
  )
  parser.add_argument(
      "--to",
      dest="target",
      required=True,
      help="Target Spark version, e.g. 4.1.2 (a patch pins its release tag).",
  )
  parser.add_argument(
      "--out",
      required=True,
      help=(
          "Output directory for the notes alone, e.g."
          " migration_notes_<app_id>_temp. The files of an earlier run in it"
          " are deleted first."
      ),
  )
  return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
  """CLI entry point for fetching Apache Spark migration notes."""
  args = _parse_args(argv)
  if not args.out.strip() or (
      os.path.lexists(args.out)
      and (os.path.islink(args.out) or not os.path.isdir(args.out))
  ):
    print(
        f"Error: --out={args.out} must be a non-symlink directory.",
        file=sys.stderr,
    )
    return 2
  if os.path.isdir(args.out):
    try:
      others = clear_output(args.out)
    except OSError as e:
      print(f"Error: couldn't clean --out={args.out} ({e}).", file=sys.stderr)
      return 2
    if others:
      print(
          "Error: the script doesn't overwrite files that it didn't write:"
          f" {', '.join(others)}. Pass an --out directory for the notes alone,"
          " e.g. migration_notes_<app_id>_temp.",
          file=sys.stderr,
      )
      return 2
  try:
    source = parse_version(args.source)
    target = parse_version(args.target)
  except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 2
  if _lower_bound(source) > _upper_bound(target):
    print(
        f"Error: the source Spark version {args.source} is newer than the"
        f" target {args.target}.",
        file=sys.stderr,
    )
    return 2

  docs_url = _published_guides(target)
  target_refs = release_refs(target)
  with concurrent.futures.ThreadPoolExecutor(
      max_workers=_MAX_PARALLEL_FETCHES
  ) as pool:
    source_index = pool.submit(resolve_ref, release_refs(source))
    try:
      ref, target_index = resolve_ref(target_refs)
    except FetchError as e:
      print(
          f"Error: couldn't download the migration guides ({e}). Read them"
          f" from the guides linked at {docs_url}, or report them as not"
          " checked.",
          file=sys.stderr,
      )
      return 1
    if ref is None:
      print(
          "Error: no Apache Spark release tag or branch found for"
          f" {args.target} (tried {', '.join(target_refs)}). Check the target"
          " Spark version on the component page.",
          file=sys.stderr,
      )
      return 2
    # Each guide falls back to master on its own, so they download in
    # parallel.
    guides = [
        pool.submit(fetch_guide, guide, (ref, "master"), source, target)
        for guide in GUIDES
    ]
    minimums = pool.submit(
        pyspark_minimums, list(dict.fromkeys((ref, target_refs[-1])))
    )
    results = [future.result() for future in guides]
    try:
      source_ref, source_index_text = source_index.result()
    except FetchError:
      source_ref, source_index_text = None, None
    where, minimum_versions = minimums.result()

  try:
    os.makedirs(args.out, exist_ok=True)
    for result in results:
      if result.sections:
        result.output_path = os.path.join(args.out, result.guide.key + ".md")
        write_guide(result, result.output_path, args.source, args.target)
  except OSError as e:
    print(f"Error: couldn't write to --out={args.out} ({e}).", file=sys.stderr)
    return 2

  lines = [f"{_INDEX_HEADER}{args.source} -> {args.target}:"]
  lines += [_describe(result) for result in results]
  lines.append("Supported runtimes (docs/index.md):")
  lines.append(_runtime_line(args.source, source_ref, source_index_text))
  lines.append(_runtime_line(args.target, ref, target_index))
  if minimum_versions:
    lines.append(
        f"PySpark {args.target} minimum versions ({where}): "
        + ", ".join(f"{k} {v}" for k, v in minimum_versions.items())
    )
  else:
    lines.append(f"PySpark {args.target} minimum versions: unavailable")
  lines.append(
      "Check every note in these files against the job"
      ' (spark_migration_reference.md, "Spark Migration Notes").'
  )
  index = "\n".join(lines)
  try:
    with open(os.path.join(args.out, _INDEX_FILE), "w", encoding="utf-8") as f:
      f.write(index + "\n")
  except OSError as e:
    print(f"Error: couldn't write to --out={args.out} ({e}).", file=sys.stderr)
    return 2
  print(index)

  failed = [
      result.guide.key
      for result in results
      if result.error or result.ref is None
  ]
  if failed:
    print(
        f"Error: couldn't download {', '.join(failed)}. Read the same sections"
        f" from the guides linked at {docs_url}, or report them as not"
        " checked.",
        file=sys.stderr,
    )
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
