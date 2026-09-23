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

"""High-performance, memory-safe streaming reader for Spark logs and event logs in GCS.

Supports:
- HTTP range reads and tailing (last N lines / bytes) without loading full files
into memory
- Streaming on-the-fly decompression for .gz / .gzip and .zst / .zstd
- Streaming single-pass summarization of Spark JSON-lines event logs
- Context-aware substring and regex search across multi-GB logs
- Reading line ranges (start_line to end_line)
"""

import argparse
import collections
import gzip
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from typing import Any, Dict, Generator, List, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

# Zstandard decompression is resolved in preference order so that no third-party
# install is required on modern interpreters:
#   1. compression.zstd - standard library from Python 3.14 (PEP 784).
#   2. zstandard        - third-party package, if the user happens to have it.
#   3. zstd CLI         - external binary fallback, handled at call time.
try:
  # pylint: disable=g-import-not-at-top
  from compression import zstd as _stdlib_zstd

  HAS_STDLIB_ZSTD = True
except ImportError:
  HAS_STDLIB_ZSTD = False

try:
  # pylint: disable=g-import-not-at-top
  import zstandard

  HAS_ZSTD = True
except ImportError:
  HAS_ZSTD = False

LARGE_FILE_THRESHOLD_BYTES = 20 * 1024 * 1024  # 20 MB
# Upper bound on a single --action=read_range request. Reading an unbounded
# range would flood the agent's context window with log text.
MAX_RANGE_LINES = 5000
GZIP_MAGIC = b"\x1f\x8b"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def parse_gcs_uri(uri: str) -> Tuple[Optional[str], Optional[str]]:
  """Parses a gs:// or https://storage.googleapis.com URI into (bucket, object_path)."""
  if uri.startswith("gs://"):
    clean = uri[len("gs://") :]
    parts = clean.split("/", 1)
    bucket = parts[0]
    object_name = parts[1] if len(parts) > 1 else ""
    return bucket, object_name
  elif uri.startswith("https://storage.googleapis.com/"):
    clean = uri[len("https://storage.googleapis.com/") :]
    parts = clean.split("/", 1)
    bucket = parts[0]
    object_name = parts[1] if len(parts) > 1 else ""
    return bucket, object_name
  elif uri.startswith("https://storage.cloud.google.com/"):
    clean = uri[len("https://storage.cloud.google.com/") :]
    parts = clean.split("/", 1)
    bucket = parts[0]
    object_name = parts[1] if len(parts) > 1 else ""
    return bucket, object_name
  return None, None


class _ProcessStream(io.RawIOBase):
  """Reads a child process's stdout and reaps the child when closed.

  `subprocess.Popen(...).stdout` on its own leaks a zombie process and hides a
  non-zero exit status, so a failed `gcloud storage cat` looks identical to an
  empty file. This wrapper waits for the child on close and raises if it
  failed, so authentication and permission errors are reported instead of
  being silently rendered as "no matching lines".
  """

  def __init__(self, proc: "subprocess.Popen[bytes]", description: str):
    self._proc = proc
    self._description = description

  def readable(self) -> bool:
    return True

  def readinto(self, b) -> int:
    assert self._proc.stdout is not None
    return self._proc.stdout.readinto(b)

  def close(self) -> None:
    if self._proc.poll() is None:
      # The caller may stop reading early (e.g. after --max_matches hits).
      self._proc.terminate()
    if self._proc.stdout is not None:
      self._proc.stdout.close()
    if self._proc.stderr is not None:
      stderr = self._proc.stderr.read().decode("utf-8", errors="replace")
      self._proc.stderr.close()
    else:
      stderr = ""
    returncode = self._proc.wait()
    super().close()
    # -15/-9 mean we terminated it deliberately after reading enough.
    if returncode not in (0, -signal.SIGTERM, -signal.SIGKILL):
      detail = stderr.strip() or f"exit code {returncode}"
      raise RuntimeError(f"{self._description} failed: {detail}")


class GcsStreamReader:
  """Streams byte ranges or files from GCS or local filesystem without buffering the full file."""

  def __init__(self, uri: str):
    self.uri = uri
    self.bucket, self.object_name = parse_gcs_uri(uri)
    self.is_gcs = self.bucket is not None
    self._cached_size: Optional[int] = None
    self._cached_compressed: Optional[bool] = None

  def get_size(self) -> Optional[int]:
    """Returns the total size of the file in bytes, or None if unknown.

    Returns:
      The object size, or None when it could not be determined (for example
      because the object does not exist or the caller lacks permission).
      `None` is deliberately distinct from `0` so that an unreadable object is
      never reported as an empty one.

    Raises:
      FileNotFoundError: If the URI names a local path that does not exist. A
        missing local file is a caller mistake worth surfacing immediately,
        whereas an unreadable GCS object may simply reflect a transient error
        or missing permission and is reported as `None`.
    """
    if self._cached_size is not None:
      return self._cached_size

    if not self.is_gcs:
      if os.path.exists(self.uri):
        self._cached_size = os.path.getsize(self.uri)
        return self._cached_size
      raise FileNotFoundError(f"Local file not found: {self.uri}")

    try:
      cmd = [
          "gcloud",
          "storage",
          "objects",
          "describe",
          self.uri,
          "--format=value(size)",
      ]
      out = subprocess.check_output(
          cmd, stderr=subprocess.DEVNULL, text=True, timeout=120
      ).strip()
      if out and out.isdigit():
        self._cached_size = int(out)
        return self._cached_size
    except (subprocess.SubprocessError, OSError, ValueError):
      pass

    return None

  def open_range_stream(
      self, start_byte: int, end_byte: Optional[int] = None
  ) -> io.BufferedReader:
    """Returns a readable binary stream for the byte range [start_byte, end_byte].

    Args:
      start_byte: First byte to read, inclusive.
      end_byte: Last byte to read, inclusive. `None` reads to end of object.

    Returns:
      A binary stream positioned at `start_byte`.

    Raises:
      RuntimeError: If no transport could serve the range. The range is never
        silently widened, because callers rely on it to bound memory use.
    """
    if not self.is_gcs:
      f = open(self.uri, "rb")
      f.seek(start_byte)
      if end_byte is not None:
        length = max(0, end_byte - start_byte + 1)
        data = f.read(length)
        f.close()
        return io.BufferedReader(io.BytesIO(data))
      return f

    if end_byte is not None:
      range_header = f"bytes={start_byte}-{end_byte}"
      gcloud_range = f"{start_byte}-{end_byte}"
    else:
      range_header = f"bytes={start_byte}-"
      gcloud_range = f"{start_byte}-"

    # Preferred path: a real HTTP Range request against the JSON API.
    try:
      token_cmd = ["gcloud", "auth", "print-access-token"]
      token = subprocess.check_output(
          token_cmd, stderr=subprocess.DEVNULL, text=True, timeout=60
      ).strip()
      if token and self.bucket and self.object_name:
        encoded_obj = urllib.parse.quote(self.object_name, safe="")
        url = f"https://storage.googleapis.com/storage/v1/b/{self.bucket}/o/{encoded_obj}?alt=media"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}", "Range": range_header},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        return io.BufferedReader(resp)
    except (
        subprocess.SubprocessError,
        OSError,
        ValueError,
        urllib.error.URLError,
    ):
      pass

    # Fallback: `gcloud storage cat -r` performs a server-side range read too.
    # It must keep the range: dropping it would stream the whole object and
    # blow up memory on the multi-gigabyte logs this script exists to handle.
    try:
      cmd = ["gcloud", "storage", "cat", "-r", gcloud_range, self.uri]
      proc = subprocess.Popen(
          cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
      )
      if proc.stdout:
        return io.BufferedReader(
            _ProcessStream(proc, f"'gcloud storage cat -r {gcloud_range}'")
        )
    except (subprocess.SubprocessError, OSError, ValueError):
      pass

    raise RuntimeError(
        f"Failed to stream byte range {range_header} from {self.uri}. Check"
        " that the object exists and that you are authenticated (run"
        " 'gcloud auth application-default login')."
    )

  def open_full_stream(self) -> io.BufferedReader:
    """Returns a readable binary stream from the beginning of the file."""
    if not self.is_gcs:
      return open(self.uri, "rb")

    try:
      token_cmd = ["gcloud", "auth", "print-access-token"]
      token = subprocess.check_output(
          token_cmd, stderr=subprocess.DEVNULL, text=True, timeout=60
      ).strip()
      if token and self.bucket and self.object_name:
        encoded_obj = urllib.parse.quote(self.object_name, safe="")
        url = f"https://storage.googleapis.com/storage/v1/b/{self.bucket}/o/{encoded_obj}?alt=media"
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {token}"}
        )
        resp = urllib.request.urlopen(req, timeout=120)
        return io.BufferedReader(resp)
    except (
        subprocess.SubprocessError,
        OSError,
        ValueError,
        urllib.error.URLError,
    ):
      pass

    cmd = ["gcloud", "storage", "cat", self.uri]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.stdout:
      return io.BufferedReader(_ProcessStream(proc, "'gcloud storage cat'"))
    raise RuntimeError(f"Unable to open stream for {self.uri}")

  def is_compressed(self) -> bool:
    """Reports whether the object is gzip/zstd compressed.

    Checks the extension first, then falls back to reading the first four
    bytes. Dataproc event logs are frequently compressed but carry no
    extension, and treating those as plain text yields binary garbage.

    Returns:
      True if the object appears to be compressed.
    """
    if self._cached_compressed is not None:
      return self._cached_compressed

    if any(self.uri.endswith(ext) for ext in (".gz", ".gzip", ".zst", ".zstd")):
      self._cached_compressed = True
      return True

    try:
      stream = self.open_range_stream(0, 3)
      try:
        header = stream.read(4)
      finally:
        stream.close()
      self._cached_compressed = header.startswith(
          GZIP_MAGIC
      ) or header.startswith(ZSTD_MAGIC)
    except (OSError, RuntimeError, ValueError):
      self._cached_compressed = False
    return self._cached_compressed

  def resolve_uri(self) -> str:
    """Resolves a Dataproc `driveroutput` prefix to the first real object.

    `driverOutputResourceUri` from `gcloud dataproc jobs describe` is a
    *prefix*: the actual objects are `driveroutput.000000000`,
    `driveroutput.000000001`, and so on. Passing the prefix through verbatim
    fails, which is the common path for every cluster job.

    Returns:
      The resolved URI, or the original if no resolution was needed.
    """
    if not self.is_gcs or not self.uri.rstrip("/").endswith("driveroutput"):
      return self.uri

    base = self.uri.rstrip("/")
    try:
      out = subprocess.check_output(
          ["gcloud", "storage", "ls", f"{base}*"],
          stderr=subprocess.DEVNULL,
          text=True,
          timeout=120,
      )
      candidates = sorted(l.strip() for l in out.splitlines() if l.strip())
      if candidates:
        return candidates[0]
    except (subprocess.SubprocessError, OSError, ValueError):
      pass

    # Fall back to the conventional first shard.
    return f"{base}.000000000"


def _sniff_compression(raw_stream: io.BufferedReader) -> Optional[str]:
  """Peeks at the leading bytes to identify the compression format.

  Dataproc writes Spark event logs with no file extension
  (`application_1700000000000_0001`) yet still compresses them, so relying on
  the URI suffix alone silently feeds compressed bytes to the UTF-8 decoder.

  Args:
    raw_stream: A buffered binary stream positioned at the start of the object.

  Returns:
    "gz", "zst", or None if the content does not look compressed.
  """
  try:
    header = raw_stream.peek(4)[:4]
  except (OSError, ValueError, AttributeError):
    return None
  if header.startswith(GZIP_MAGIC):
    return "gz"
  if header.startswith(ZSTD_MAGIC):
    return "zst"
  return None


def get_decompressed_line_generator(
    raw_stream: io.BufferedReader, uri: str
) -> Generator[str, None, None]:
  """Wraps a binary stream in streaming decompressors (.gz, .zst) and yields decoded lines."""
  is_gz = uri.endswith(".gz") or uri.endswith(".gzip")
  is_zst = uri.endswith(".zst") or uri.endswith(".zstd")

  if not is_gz and not is_zst:
    # Fall back to content sniffing for extension-less objects.
    sniffed = _sniff_compression(raw_stream)
    is_gz = sniffed == "gz"
    is_zst = sniffed == "zst"

  if is_gz:
    gz_file = gzip.GzipFile(fileobj=raw_stream, mode="rb")
    text_stream = io.TextIOWrapper(gz_file, encoding="utf-8", errors="replace")
    try:
      for line in text_stream:
        yield line
    finally:
      text_stream.close()
      raw_stream.close()
  elif is_zst:
    if HAS_STDLIB_ZSTD:
      # Python 3.14+ standard library; no third-party install required.
      stream_reader = _stdlib_zstd.ZstdFile(raw_stream, "rb")
      text_stream = io.TextIOWrapper(
          stream_reader, encoding="utf-8", errors="replace"
      )
      for line in text_stream:
        yield line
      text_stream.close()
    elif HAS_ZSTD:
      dctx = zstandard.ZstdDecompressor()
      stream_reader = dctx.stream_reader(raw_stream)
      text_stream = io.TextIOWrapper(
          stream_reader, encoding="utf-8", errors="replace"
      )
      for line in text_stream:
        yield line
      text_stream.close()
    elif shutil.which("zstd"):
      # Fall back to the zstd CLI when no Python module is importable.
      proc = subprocess.Popen(
          ["zstd", "-d", "-c"],
          stdin=raw_stream,
          stdout=subprocess.PIPE,
          stderr=subprocess.DEVNULL,
      )
      if not proc.stdout:
        raise RuntimeError("Failed to start the zstd decompression process.")
      text_stream = io.TextIOWrapper(
          proc.stdout, encoding="utf-8", errors="replace"
      )
      for line in text_stream:
        yield line
      text_stream.close()
    else:
      raise RuntimeError(
          "Reading .zst files requires Zstandard support, which is unavailable."
          " Use Python 3.14+ (which bundles the standard library"
          " 'compression.zstd' module), or install one of:\n"
          "  pip install zstandard\n"
          "  apt-get install zstd   (or: brew install zstd)"
      )
  else:
    text_stream = io.TextIOWrapper(
        raw_stream, encoding="utf-8", errors="replace"
    )
    try:
      for line in text_stream:
        yield line
    finally:
      text_stream.close()
      raw_stream.close()


def action_info(reader: GcsStreamReader) -> None:
  """Prints file metadata and size assessment."""
  size = reader.get_size()
  is_compressed = reader.is_compressed()

  print(f"=== File Metadata for: {reader.uri} ===")
  if size is None:
    print("Size: UNKNOWN (could not read object metadata)")
    print(f"Compressed: {is_compressed}")
    print(
        "Recommendation: The object size could not be determined. Verify the"
        " URI is correct and that you are authenticated"
        " ('gcloud auth application-default login'). Treat the file as large"
        " and use streaming actions only: tail, search, read_range, or"
        " summarize_events."
    )
    return

  is_large = size > LARGE_FILE_THRESHOLD_BYTES
  size_mb = size / (1024 * 1024)
  print(f"Size: {size} bytes ({size_mb:.2f} MB)")
  print(f"Compressed: {is_compressed}")
  print(f"Is Large File (>20MB): {is_large}")
  if is_large:
    print(
        "Recommendation: File exceeds 20MB. DO NOT download or cat full file."
        " Use streaming actions: tail, search, read_range, or summarize_events."
    )
  else:
    print(
        "Recommendation: File is under 20MB. Streaming tail and search are"
        " still recommended to keep prompt context clean."
    )


def action_tail(
    reader: GcsStreamReader, num_lines: int = 100, tail_bytes: int = 524288
) -> None:
  """Tails the last num_lines of a log file without reading preceding gigabytes."""
  size = reader.get_size()
  is_compressed = reader.is_compressed()

  if is_compressed or not size:
    # Compressed files must be streamed forward; buffer last N lines in a
    # deque so memory stays bounded by num_lines rather than by file size.
    stream = reader.open_full_stream()
    try:
      deque_lines: collections.deque[str] = collections.deque(maxlen=num_lines)
      for line in get_decompressed_line_generator(stream, reader.uri):
        deque_lines.append(line)
    finally:
      stream.close()
    for line in deque_lines:
      sys.stdout.write(line)
    return

  # Plain-text files can use byte-range seeking from the end.
  start_byte = max(0, size - tail_bytes)
  read_len = size - start_byte
  stream = reader.open_range_stream(start_byte, size - 1)
  try:
    # Bound the read explicitly: this is the guarantee that a tail of a 5 GB
    # driver log costs tail_bytes of memory and not 5 GB.
    content = stream.read(read_len).decode("utf-8", errors="replace")
  finally:
    stream.close()

  lines = content.splitlines(keepends=True)
  # If we didn't start at byte 0, the first line is likely partially sliced.
  if start_byte > 0 and lines:
    lines = lines[1:]

  selected = lines[-num_lines:]
  for line in selected:
    sys.stdout.write(line)


def action_search(
    reader: GcsStreamReader,
    substring: Optional[str],
    regex: Optional[str],
    context: int = 5,
    max_matches: int = 20,
    ignore_case: bool = False,
) -> None:
  """Searches for substring or regex across the stream and prints matches with surrounding context lines."""
  stream = reader.open_full_stream()
  flags = re.IGNORECASE if ignore_case else 0
  pattern = re.compile(regex, flags) if regex else None
  needle = substring.lower() if (substring and ignore_case) else substring

  pre_context = collections.deque(maxlen=context)
  line_num = 0
  matches_found = 0
  post_context_remaining = 0

  print(f"=== Searching '{substring or regex}' in {reader.uri} ===")

  try:
    for line in get_decompressed_line_generator(stream, reader.uri):
      line_num += 1
      haystack = line.lower() if ignore_case else line
      is_match = False
      if needle and needle in haystack:
        is_match = True
      elif pattern and pattern.search(line):
        is_match = True

      if is_match:
        matches_found += 1
        print(f"\n--- Match #{matches_found} at line {line_num} ---")
        # Print previous context
        for prev_num, prev_line in pre_context:
          print(f"  {prev_num:6d} | {prev_line.rstrip()}")
        # Print match line
        print(f"> {line_num:6d} | {line.rstrip()}")
        pre_context.clear()
        post_context_remaining = context
        if matches_found >= max_matches:
          print(
              f"\n[Reached maximum match limit of {max_matches}. Stopping"
              " search.]"
          )
          break
      elif post_context_remaining > 0:
        print(f"  {line_num:6d} | {line.rstrip()}")
        post_context_remaining -= 1
      else:
        pre_context.append((line_num, line))
  finally:
    stream.close()

  print(
      f"\n=== Search complete. Total matches found: {matches_found} "
      f"(scanned {line_num} lines) ==="
  )
  if matches_found == 0:
    print(
        "Hint: no matches. Spark messages vary in casing and wording -- retry"
        " with --ignore_case, or with a broader --regex."
    )


def action_read_range(
    reader: GcsStreamReader, start_line: int, end_line: int
) -> None:
  """Reads a specific range of lines [start_line, end_line] (1-indexed)."""
  if end_line < start_line:
    raise ValueError(
        f"--end_line ({end_line}) must not be less than --start_line"
        f" ({start_line})."
    )
  if end_line - start_line + 1 > MAX_RANGE_LINES:
    raise ValueError(
        f"Requested {end_line - start_line + 1} lines, which exceeds the"
        f" {MAX_RANGE_LINES}-line cap. Dumping an unbounded range defeats the"
        " purpose of streaming and will flood the context window. Narrow the"
        " range, or use --action=search to locate the region of interest"
        " first."
    )

  stream = reader.open_full_stream()
  current_line = 0
  try:
    for line in get_decompressed_line_generator(stream, reader.uri):
      current_line += 1
      if current_line >= start_line and current_line <= end_line:
        sys.stdout.write(f"{current_line:6d} | {line}")
      elif current_line > end_line:
        break
  finally:
    stream.close()


def action_summarize_events(reader: GcsStreamReader) -> None:
  """Streams through a Spark event log (JSON-lines) and produces an executive summary."""
  stream = reader.open_full_stream()

  app_id = "Unknown"
  app_name = "Unknown"
  spark_user = "Unknown"
  spark_version = "Unknown"
  start_time = None
  end_time = None

  failed_stages: List[Dict[str, Any]] = []
  failed_tasks: List[Dict[str, Any]] = []
  executors_removed: List[Dict[str, Any]] = []
  spill_events: List[Dict[str, Any]] = []

  total_jobs = 0
  failed_jobs = 0
  total_stages = 0
  total_tasks = 0
  total_gc_time = 0
  event_type_counts: Dict[str, int] = collections.defaultdict(int)

  line_count = 0

  for line in get_decompressed_line_generator(stream, reader.uri):
    line_count += 1
    line_str = line.strip()
    if not line_str or not line_str.startswith("{"):
      continue

    try:
      event = json.loads(line_str)
    except (json.JSONDecodeError, ValueError):
      continue

    event_type = event.get("Event")
    if event_type:
      event_type_counts[event_type] += 1

    if event_type == "SparkListenerLogStart":
      spark_version = event.get("Spark Version", spark_version)
    elif event_type == "SparkListenerApplicationStart":
      app_id = event.get("App ID", app_id)
      app_name = event.get("App Name", app_name)
      spark_user = event.get("User", spark_user)
      start_time = event.get("Timestamp")
    elif event_type == "SparkListenerApplicationEnd":
      end_time = event.get("Timestamp")
    elif event_type == "SparkListenerJobStart":
      total_jobs += 1
    elif event_type == "SparkListenerJobEnd":
      job_result = event.get("Job Result", {})
      if job_result.get("Result") not in (None, "JobSucceeded"):
        failed_jobs += 1
    elif event_type == "SparkListenerStageSubmitted":
      total_stages += 1
    elif event_type == "SparkListenerStageCompleted":
      stage_info = event.get("Stage Info", {})
      s_id = stage_info.get("Stage ID", -1)
      s_name = stage_info.get("Stage Name", "")
      failure_reason = stage_info.get("Failure Reason")
      num_tasks = stage_info.get("Number of Tasks", 0)

      # Check metrics for spills
      accumulables = stage_info.get("Accumulables", [])
      mem_spill = 0
      disk_spill = 0
      for acc in accumulables:
        acc_name = acc.get("Name", "")
        clean_acc = acc_name.lower().replace(" ", "").replace("_", "")
        if "memorybytesspilled" in clean_acc:
          mem_spill = acc.get("Value", 0)
        elif "diskbytesspilled" in clean_acc:
          disk_spill = acc.get("Value", 0)

      if mem_spill > 0 or disk_spill > 0:
        spill_events.append({
            "stage_id": s_id,
            "stage_name": s_name,
            "mem_spill_bytes": mem_spill,
            "disk_spill_bytes": disk_spill,
            "line": line_count,
        })

      if failure_reason:
        failed_stages.append({
            "stage_id": s_id,
            "stage_name": s_name,
            "num_tasks": num_tasks,
            "failure_reason": str(failure_reason)[:300],
            "line": line_count,
        })
    elif event_type == "SparkListenerTaskEnd":
      total_tasks += 1
      task_metrics = event.get("Task Metrics", {})
      total_gc_time += task_metrics.get("JVM GC Time", 0) or 0
      task_end_reason = event.get("Task End Reason", {})
      reason_type = task_end_reason.get("Reason")
      if reason_type and reason_type != "Success":
        task_info = event.get("Task Info", {})
        # Spark's JsonProtocol writes ExceptionFailure as a flat object with
        # "Class Name" and "Description"; there is no nested "Exception"
        # object, so the previous lookup never matched and always fell back to
        # dumping the raw reason dict.
        exception_class = task_end_reason.get("Class Name")
        description = (
            task_end_reason.get("Description")
            # FetchFailed / ExecutorLostFailure carry their detail elsewhere.
            or task_end_reason.get("Message")
            or task_end_reason.get("Loss Reason")
            or task_end_reason.get("Kill Reason")
        )
        if exception_class and description:
          detail = f"{exception_class}: {description}"
        else:
          detail = description or exception_class or str(task_end_reason)
        failed_tasks.append({
            "task_id": task_info.get("Task ID"),
            "stage_id": event.get("Stage ID"),
            "index": task_info.get("Index"),
            "attempt": task_info.get("Attempt"),
            "executor_id": task_info.get("Executor ID"),
            "host": task_info.get("Host"),
            "reason": reason_type,
            "exception": detail[:300],
            "line": line_count,
        })
    elif event_type == "SparkListenerExecutorRemoved":
      executors_removed.append({
          "executor_id": event.get("Executor ID"),
          # Spark emits "Removed Reason" here, not "Reason". Reading the wrong
          # key made every executor loss report a reason of None -- exactly the
          # signal needed to distinguish OOM kills from preemption.
          "reason": event.get("Removed Reason"),
          "removed_time": event.get("Timestamp"),
          "line": line_count,
      })

  stream.close()

  # Format executive summary in markdown
  print("## Spark Event Log Executive Summary\n")
  print(f"- **Source URI**: `{reader.uri}`")
  print(f"- **Application ID**: `{app_id}`")
  print(f"- **Application Name**: `{app_name}`")
  print(f"- **User**: `{spark_user}`")
  print(f"- **Spark Version**: `{spark_version}`")
  if start_time and end_time:
    duration_sec = (end_time - start_time) / 1000.0
    print(
        f"- **Duration**: `{duration_sec:.2f}s` (Start: `{start_time}`, End:"
        f" `{end_time}`)"
    )
  print(f"- **Jobs**: `{total_jobs}` total, `{failed_jobs}` failed")
  print(
      f"- **Stages**: `{total_stages}` submitted, `{len(failed_stages)}` failed"
  )
  print(f"- **Tasks**: `{total_tasks}` completed, `{len(failed_tasks)}` failed")
  print(f"- **Total JVM GC Time**: `{total_gc_time} ms`")
  print(f"- **Total Event Lines Processed**: `{line_count}`\n")

  if event_type_counts:
    top_events = sorted(
        event_type_counts.items(), key=lambda kv: kv[1], reverse=True
    )[:10]
    print("### Event Type Histogram (top 10)")
    for name, count in top_events:
      print(f"- `{name}`: {count}")
    print()

  if failed_stages:
    print(f"### Failed Stages ({len(failed_stages)})")
    for fs in failed_stages[:10]:
      print(
          f"- **Stage {fs['stage_id']}** (`{fs['stage_name']}`) at line"
          f" {fs['line']}:"
      )
      print(f"  - Failure Reason: `{fs['failure_reason']}`")
    print()
  else:
    print("### Failed Stages: None detected.\n")

  if failed_tasks:
    print(f"### Failed Tasks ({len(failed_tasks)} total, showing up to 20)")
    for ft in failed_tasks[:20]:
      print(
          f"- **Task {ft['task_id']}** (Stage {ft['stage_id']}, Index"
          f" {ft['index']}, Attempt {ft['attempt']}, Executor"
          f" {ft['executor_id']}, Host {ft['host']}) at line {ft['line']}:"
      )
      print(f"  - Reason: `{ft['reason']}`")
      print(f"  - Details: `{ft['exception']}`")
    print()

  if executors_removed:
    print(f"### Lost / Removed Executors ({len(executors_removed)})")
    for er in executors_removed[:10]:
      print(
          f"- Executor `{er['executor_id']}` at line {er['line']}: Reason:"
          f" `{er['reason']}`"
      )
    print()

  if spill_events:
    print(f"### Memory/Disk Spill Events ({len(spill_events)})")
    for sp in spill_events[:10]:
      print(
          f"- Stage {sp['stage_id']}: Mem Spilled = {sp['mem_spill_bytes']}"
          f" bytes, Disk Spilled = {sp['disk_spill_bytes']} bytes (line"
          f" {sp['line']})"
      )
    print()


def main():
  parser = argparse.ArgumentParser(
      description="High-performance streaming GCS log reader for Spark"
  )
  parser.add_argument(
      "--uri", required=True, help="GCS URI (gs://...) or local file path"
  )
  parser.add_argument(
      "--action",
      choices=[
          "info",
          "tail",
          "search",
          "read_range",
          "summarize_events",
          "head",
      ],
      default="info",
  )
  parser.add_argument(
      "--lines",
      type=int,
      default=100,
      help="Number of lines to read for head/tail",
  )
  parser.add_argument(
      "--bytes", type=int, default=524288, help="Byte chunk size for tail"
  )
  parser.add_argument(
      "--substring", type=str, default=None, help="Substring to search"
  )
  parser.add_argument("--regex", type=str, default=None, help="Regex to search")
  parser.add_argument(
      "--start_line",
      type=int,
      default=1,
      help="Start line for read_range (1-indexed)",
  )
  parser.add_argument(
      "--end_line",
      type=int,
      default=100,
      help="End line for read_range (1-indexed)",
  )
  parser.add_argument(
      "--context",
      type=int,
      default=5,
      help="Lines of context around search matches",
  )
  parser.add_argument(
      "--max_matches",
      type=int,
      default=20,
      help="Maximum search matches to print",
  )
  parser.add_argument(
      "--ignore_case",
      action="store_true",
      help=(
          "Match --substring and --regex case-insensitively. Spark stack"
          " traces mix casing (Error/ERROR/error), so this is usually what you"
          " want when hunting for failures."
      ),
  )

  args = parser.parse_args()
  reader = GcsStreamReader(args.uri)

  # `driverOutputResourceUri` is a prefix; the real objects are
  # `driveroutput.000000000`, etc. Resolve it so the common cluster-job path
  # works without the caller having to know this.
  resolved = reader.resolve_uri()
  if resolved != args.uri:
    print(f"Note: resolved driver output prefix to {resolved}", file=sys.stderr)
    reader = GcsStreamReader(resolved)

  try:
    if args.action == "info":
      action_info(reader)
    elif args.action == "tail":
      action_tail(reader, num_lines=args.lines, tail_bytes=args.bytes)
    elif args.action == "search":
      if not args.substring and not args.regex:
        print(
            "Error: --substring or --regex is required for search action.",
            file=sys.stderr,
        )
        sys.exit(1)
      action_search(
          reader,
          substring=args.substring,
          regex=args.regex,
          context=args.context,
          max_matches=args.max_matches,
          ignore_case=args.ignore_case,
      )
    elif args.action == "read_range":
      action_read_range(
          reader, start_line=args.start_line, end_line=args.end_line
      )
    elif args.action == "summarize_events":
      action_summarize_events(reader)
    elif args.action == "head":
      stream = reader.open_full_stream()
      try:
        count = 0
        for line in get_decompressed_line_generator(stream, reader.uri):
          sys.stdout.write(line)
          count += 1
          if count >= args.lines:
            break
      finally:
        stream.close()
  except BrokenPipeError:
    # The consumer stopped reading (e.g. piped into `head`); not an error.
    pass
  except (FileNotFoundError, RuntimeError, ValueError) as e:
    # A raw traceback here would be dumped verbatim into an agent's context
    # window and read as a tool crash. Emit one actionable line instead.
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
  except KeyboardInterrupt:
    sys.exit(130)


if __name__ == "__main__":
  main()
