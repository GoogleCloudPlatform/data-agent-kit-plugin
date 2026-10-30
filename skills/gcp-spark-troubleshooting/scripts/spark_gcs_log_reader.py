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
import contextlib
import gzip
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from typing import Any, Dict, Generator, List, Optional, Set, Tuple
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

# pylint: disable=g-import-not-at-top
# The sibling script is importable because Python puts the running script's
# directory on sys.path (and the tests/BUILD add scripts/ explicitly). Suppress
# bytecode writes so direct CLI runs do not leave __pycache__ in the skill dir.
_orig_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
  import spark_applications
finally:
  sys.dont_write_bytecode = _orig_dont_write_bytecode

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


def _v2_shard_sort_key(uri: str) -> Tuple[int, int, str]:
  """Sorts rolling eventlog_v2 `events_<N>_*` shards numerically by index."""
  leaf = uri.rstrip("/").rsplit("/", 1)[-1]
  match = re.search(r"^events_(\d+)", leaf)
  if match:
    return (0, int(match.group(1)), leaf)
  return (1, 0, leaf)


class GcsStreamReader:
  """Streams byte ranges or files from GCS or local filesystem without buffering the full file."""

  def __init__(self, uri: str, shard_uris: Optional[List[str]] = None):
    self.uri = uri
    self.bucket, self.object_name = parse_gcs_uri(uri)
    self.is_gcs = self.bucket is not None
    self._cached_size: Optional[int] = None
    self._cached_compressed: Optional[bool] = None
    self._shard_uris: Optional[List[str]] = (
        list(shard_uris) if shard_uris else None
    )

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

    base = self.uri.rstrip("/")
    if self._shard_uris is None and (
        (not self.is_gcs and os.path.isdir(base))
        or (self.is_gcs and re.search(r"/eventlog_v2_[^/]+\Z", base))
    ):
      resolved = self.resolve_uris()
      if resolved and (len(resolved) > 1 or resolved[0] != self.uri):
        self._shard_uris = resolved

    if self._shard_uris and (
        len(self._shard_uris) > 1 or self._shard_uris[0] != self.uri
    ):
      if not self.is_gcs:
        total = 0
        for s_uri in self._shard_uris:
          if not os.path.exists(s_uri):
            raise FileNotFoundError(f"Local file not found: {s_uri}")
          total += os.path.getsize(s_uri)
        self._cached_size = total
        return self._cached_size

      try:
        cmd = [
            "gcloud",
            "storage",
            "objects",
            "list",
            *self._shard_uris,
            "--format=value(size)",
        ]
        out = subprocess.check_output(
            cmd, stderr=subprocess.DEVNULL, text=True, timeout=120
        ).strip()
        sizes = [
            int(ln.strip())
            for ln in out.splitlines()
            if ln.strip().isdigit()
        ]
        if len(sizes) == len(self._shard_uris):
          self._cached_size = sum(sizes)
          return self._cached_size
      except (subprocess.SubprocessError, OSError, ValueError):
        pass

      total = 0
      for s_uri in self._shard_uris:
        shard_sz = GcsStreamReader(s_uri).get_size()
        if shard_sz is None:
          return None
        total += shard_sz
      self._cached_size = total
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

  _TOKEN_COMMANDS = (
      ("gcloud", "auth", "print-access-token"),
      ("gcloud", "auth", "application-default", "print-access-token"),
  )

  def _open_gcs_http(
      self, range_header: Optional[str], timeout: int
  ) -> Optional[io.BufferedReader]:
    """Opens a GCS JSON API media stream, retrying with ADC on HTTP 401."""
    if not (self.bucket and self.object_name):
      return None
    encoded_obj = urllib.parse.quote(self.object_name, safe="")
    url = (
        f"https://storage.googleapis.com/storage/v1/b/{self.bucket}"
        f"/o/{encoded_obj}?alt=media"
    )
    start_idx = getattr(self, "_token_cmd_idx", 0)
    for idx in range(start_idx, len(self._TOKEN_COMMANDS)):
      try:
        token = subprocess.check_output(
            list(self._TOKEN_COMMANDS[idx]),
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=60,
        ).strip()
      except (subprocess.SubprocessError, OSError, ValueError):
        continue
      if not token:
        continue
      headers = {"Authorization": f"Bearer {token}"}
      if range_header:
        headers["Range"] = range_header
      req = urllib.request.Request(url, headers=headers)
      try:
        resp = urllib.request.urlopen(
            req, timeout=timeout, context=spark_applications.ssl_context()
        )
        self._token_cmd_idx = idx
        return io.BufferedReader(resp)
      except urllib.error.HTTPError as e:
        try:
          e.close()
        except OSError:
          pass
        if e.code == 401 and idx + 1 < len(self._TOKEN_COMMANDS):
          self._token_cmd_idx = idx + 1
          continue
        return None
      except (OSError, ValueError, urllib.error.URLError):
        return None
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

    # Preferred path: a real HTTP Range request against the JSON API (with ADC
    # fallback when the user token is rejected by context-aware access).
    http_stream = self._open_gcs_http(range_header=range_header, timeout=60)
    if http_stream is not None:
      return http_stream

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

    http_stream = self._open_gcs_http(range_header=None, timeout=120)
    if http_stream is not None:
      return http_stream

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

    base = self.uri.rstrip("/")
    if self._shard_uris is None and (
        (not self.is_gcs and os.path.isdir(base))
        or (self.is_gcs and re.search(r"/eventlog_v2_[^/]+\Z", base))
    ):
      resolved = self.resolve_uris()
      if resolved and (len(resolved) > 1 or resolved[0] != self.uri):
        self._shard_uris = resolved

    if self._shard_uris and (
        len(self._shard_uris) > 1 or self._shard_uris[0] != self.uri
    ):
      for s_uri in self._shard_uris:
        if s_uri.endswith((".gz", ".gzip", ".zst", ".zstd")):
          self._cached_compressed = True
          return True
      for s_uri in self._shard_uris:
        if GcsStreamReader(s_uri).is_compressed():
          self._cached_compressed = True
          return True
      self._cached_compressed = False
      return False

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

  def resolve_uris(self) -> List[str]:
    """Resolves a Dataproc log URI or rolling eventlog_v2 dir to shard URIs."""
    base = self.uri.rstrip("/")
    has_attempt_suffix = bool(re.search(r"/application_\d+_\d+_\d+\Z", base))
    if not self.is_gcs:
      if os.path.isdir(base):
        shards = sorted(
            (
                os.path.join(base, fn)
                for fn in os.listdir(base)
                if fn.startswith("events_")
                and os.path.isfile(os.path.join(base, fn))
            ),
            key=_v2_shard_sort_key,
        )
        if shards:
          return shards
      elif not os.path.exists(base) and re.search(
          r"/application_\d+_\d+(?:_\d+)?\Z", base
      ):
        parent_dir = os.path.dirname(base)
        app_leaf = os.path.basename(base)
        v2_candidates = [os.path.join(parent_dir, f"eventlog_v2_{app_leaf}")]
        if not has_attempt_suffix and os.path.isdir(parent_dir):
          attempt_dirs: List[Tuple[int, str]] = []
          att_re = re.compile(rf"^eventlog_v2_{re.escape(app_leaf)}_(\d+)\Z")
          for entry in os.listdir(parent_dir):
            m = att_re.fullmatch(entry)
            if m:
              attempt_dirs.append(
                  (int(m.group(1)), os.path.join(parent_dir, entry))
              )
          attempt_dirs.sort(key=lambda item: -item[0])
          v2_candidates.extend(path for _, path in attempt_dirs)
        for v2_dir in v2_candidates:
          if os.path.isdir(v2_dir):
            shards = sorted(
                (
                    os.path.join(v2_dir, fn)
                    for fn in os.listdir(v2_dir)
                    if fn.startswith("events_")
                    and os.path.isfile(os.path.join(v2_dir, fn))
                ),
                key=_v2_shard_sort_key,
            )
            if shards:
              return shards
      return [self.uri]

    is_driveroutput = base.endswith("driveroutput")
    app_match = re.search(r"/application_\d+_\d+(?:_\d+)?\Z", base)
    v2_dir_match = re.search(r"/eventlog_v2_[^/]+\Z", base)

    if v2_dir_match:
      try:
        out = subprocess.check_output(
            ["gcloud", "storage", "ls", f"{base}/events_*"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=120,
        )
        shards = sorted(
            (
                l.strip()
                for l in out.splitlines()
                if l.strip()
                and not l.strip().endswith(":")
                and not l.strip().endswith("/")
            ),
            key=_v2_shard_sort_key,
        )
        if shards:
          return shards
      except (subprocess.SubprocessError, OSError, ValueError):
        pass
      return [self.uri]

    if not is_driveroutput and not app_match:
      return [self.uri]

    def _candidate_rank(cand: str) -> Optional[Tuple[int, int, int, str]]:
      if cand.endswith("/"):
        return None
      if cand == base:
        attempt = 0
      elif cand.startswith(base + "."):
        attempt = 0
      elif not is_driveroutput and not has_attempt_suffix:
        m = re.fullmatch(
            rf"{re.escape(base)}_(\d+)(?:\.[A-Za-z0-9_.-]+)?", cand
        )
        if not m:
          return None
        attempt = int(m.group(1))
      else:
        return None
      exact_rank = 0 if cand == base else 1
      inprog_rank = 1 if cand.endswith(".inprogress") else 0
      return (exact_rank, inprog_rank, -attempt, cand)

    try:
      out = subprocess.check_output(
          ["gcloud", "storage", "ls", f"{base}*"],
          stderr=subprocess.DEVNULL,
          text=True,
          timeout=120,
      )
      ranked: List[Tuple[Tuple[int, int, int, str], str]] = []
      for raw_line in out.splitlines():
        cand = raw_line.strip()
        if not cand or cand.endswith(":"):
          continue
        rk = _candidate_rank(cand)
        if rk is not None:
          ranked.append((rk, cand))
      if ranked:
        ranked.sort(key=lambda item: item[0])
        return [ranked[0][1]]
    except (subprocess.SubprocessError, OSError, ValueError):
      pass

    if app_match:
      # Check Spark 3 rolling event log v2 directory convention as a fallback.
      parent_dir, app_leaf = base.rsplit("/", 1)
      try:
        out = subprocess.check_output(
            [
                "gcloud",
                "storage",
                "ls",
                f"{parent_dir}/eventlog_v2_{app_leaf}/events_*",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=120,
        )
        shards = sorted(
            (
                l.strip()
                for l in out.splitlines()
                if l.strip()
                and not l.strip().endswith(":")
                and not l.strip().endswith("/")
            ),
            key=_v2_shard_sort_key,
        )
        if shards:
          return shards
      except (subprocess.SubprocessError, OSError, ValueError):
        pass

      if not has_attempt_suffix:
        try:
          out = subprocess.check_output(
              [
                  "gcloud",
                  "storage",
                  "ls",
                  f"{parent_dir}/eventlog_v2_{app_leaf}_*/events_*",
              ],
              stderr=subprocess.DEVNULL,
              text=True,
              timeout=120,
          )
          att_shard_re = re.compile(
              rf"/eventlog_v2_{re.escape(app_leaf)}_(\d+)/events_[^/]+\Z"
          )
          by_attempt: Dict[int, List[str]] = collections.defaultdict(list)
          for raw_line in out.splitlines():
            cand = raw_line.strip()
            if not cand or cand.endswith(":") or cand.endswith("/"):
              continue
            m = att_shard_re.search(cand)
            if m:
              by_attempt[int(m.group(1))].append(cand)
          if by_attempt:
            best_attempt = max(by_attempt)
            return sorted(by_attempt[best_attempt], key=_v2_shard_sort_key)
        except (subprocess.SubprocessError, OSError, ValueError):
          pass
      return [self.uri]

    # Fall back to the conventional first shard for driveroutput.
    return [f"{base}.000000000"]

  def resolve_uri(self) -> str:
    """Resolves a Dataproc `driveroutput` or `application_<id>` prefix in GCS.

    Returns:
      The first resolved URI, or the original if no resolution was needed.
    """
    uris = self.resolve_uris()
    return uris[0] if uris else self.uri

  def stream_lines(self) -> Generator[str, None, None]:
    """Yields decoded lines across single-file or multi-shard rolling logs."""
    shard_uris = (
        self._shard_uris
        if self._shard_uris is not None
        else self.resolve_uris()
    )
    if len(shard_uris) == 1 and shard_uris[0] == self.uri:
      stream = self.open_full_stream()
      try:
        with contextlib.closing(
            get_decompressed_line_generator(stream, self.uri)
        ) as gen:
          yield from gen
      finally:
        stream.close()
      return

    for shard_uri in shard_uris:
      shard_reader = GcsStreamReader(shard_uri)
      stream = shard_reader.open_full_stream()
      try:
        with contextlib.closing(
            get_decompressed_line_generator(stream, shard_uri)
        ) as gen:
          yield from gen
      finally:
        stream.close()


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
      try:
        for line in text_stream:
          yield line
      finally:
        text_stream.close()
        raw_stream.close()
    elif HAS_ZSTD:
      dctx = zstandard.ZstdDecompressor()
      stream_reader = dctx.stream_reader(raw_stream)
      text_stream = io.TextIOWrapper(
          stream_reader, encoding="utf-8", errors="replace"
      )
      try:
        for line in text_stream:
          yield line
      finally:
        text_stream.close()
        raw_stream.close()
    elif shutil.which("zstd"):
      # Fall back to the zstd CLI when no Python module is importable.
      proc = subprocess.Popen(
          ["zstd", "-d", "-c"],
          stdin=raw_stream,
          stdout=subprocess.PIPE,
          stderr=subprocess.DEVNULL,
      )
      if not proc.stdout:
        raw_stream.close()
        raise RuntimeError("Failed to start the zstd decompression process.")
      text_stream = io.TextIOWrapper(
          proc.stdout, encoding="utf-8", errors="replace"
      )
      try:
        for line in text_stream:
          yield line
      finally:
        text_stream.close()
        raw_stream.close()
        if proc.poll() is None:
          proc.terminate()
        try:
          proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
          proc.kill()
          proc.wait(timeout=5)
    else:
      raw_stream.close()
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
  shard_uris = reader._shard_uris  # pylint: disable=protected-access

  print(f"=== File Metadata for: {reader.uri} ===")
  if shard_uris and len(shard_uris) > 1:
    print(f"Shards: {len(shard_uris)} rolling eventlog_v2 files")
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
  shard_uris = (
      reader._shard_uris  # pylint: disable=protected-access
      if reader._shard_uris is not None  # pylint: disable=protected-access
      else reader.resolve_uris()
  )
  is_multi_shard = len(shard_uris) > 1 or (
      len(shard_uris) == 1 and shard_uris[0] != reader.uri
  )
  if is_multi_shard:
    deque_lines: collections.deque[str] = collections.deque(maxlen=num_lines)
    with contextlib.closing(reader.stream_lines()) as lines_gen:
      for line in lines_gen:
        deque_lines.append(line)
    for line in deque_lines:
      sys.stdout.write(line)
    return

  size = reader.get_size()
  is_compressed = reader.is_compressed()

  if is_compressed or not size:
    # Compressed files must be streamed forward; buffer last N lines in a
    # deque so memory stays bounded by num_lines rather than by file size.
    deque_lines = collections.deque(maxlen=num_lines)
    with contextlib.closing(reader.stream_lines()) as lines_gen:
      for line in lines_gen:
        deque_lines.append(line)
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
  flags = re.IGNORECASE if ignore_case else 0
  pattern = re.compile(regex, flags) if regex else None
  needle = substring.lower() if (substring and ignore_case) else substring

  pre_context = collections.deque(maxlen=context)
  line_num = 0
  matches_found = 0
  post_context_remaining = 0

  print(f"=== Searching '{substring or regex}' in {reader.uri} ===")

  with contextlib.closing(reader.stream_lines()) as lines_gen:
    for line in lines_gen:
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

  current_line = 0
  with contextlib.closing(reader.stream_lines()) as lines_gen:
    for line in lines_gen:
      current_line += 1
      if current_line >= start_line and current_line <= end_line:
        sys.stdout.write(f"{current_line:6d} | {line}")
      elif current_line > end_line:
        break


def _walk_spark_plan_info(
    plan_info: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
  """Flattens a SparkPlanInfo tree from SparkListenerSQLExecution events."""
  if not isinstance(plan_info, dict):
    return []
  out: List[Dict[str, Any]] = []
  stack = [plan_info]
  while stack:
    node = stack.pop(0)
    if not isinstance(node, dict):
      continue
    out.append(node)
    children = node.get("children") or []
    if isinstance(children, list):
      stack.extend(children)
  return out


def _median_int(values: List[int]) -> float:
  if not values:
    return 0.0
  ordered = sorted(values)
  mid = len(ordered) // 2
  if len(ordered) % 2 == 1:
    return float(ordered[mid])
  return (ordered[mid - 1] + ordered[mid]) / 2.0


def _format_sql_accum(val: Any, metric_type: str) -> str:
  """Formats a raw SQL accumulator value using its Spark metricType."""
  if val is None:
    return ""
  if isinstance(val, str):
    stripped = val.strip()
    if not stripped or stripped in ("0", "0 B", "0 ms", "0.0 B", "0.0 ms"):
      return ""
    if stripped.lstrip("-").isdigit():
      val = int(stripped)
    else:
      return " ".join(stripped.split())
  if isinstance(val, (int, float)):
    if val <= 0:
      return ""
    ival = int(val)
    mtype = (metric_type or "").lower()
    if mtype == "size":
      return f"{spark_applications.human_bytes(ival)} ({ival:,} B)"
    if mtype == "timing":
      return spark_applications.human_millis(ival)
    if mtype == "nstiming":
      return spark_applications.human_millis(ival / 1_000_000.0)
    return f"{ival:,}"
  return str(val)


def action_summarize_events(reader: GcsStreamReader) -> None:
  """Streams through a Spark event log (JSON-lines) and produces an executive summary."""
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
  completed_tasks_count = 0
  executors_added = 0
  executor_cores_total = 0
  total_gc_time = 0
  completed_gc_time = 0
  total_exec_run_time = 0
  peak_task_exec_mem = {
      "JVMHeapMemory": 0,
      "JVMOffHeapMemory": 0,
      "ProcessTreeJVMRSSMemory": 0,
      "ProcessTreePythonRSSMemory": 0,
  }
  unattributed_io = {
      "in_bytes": 0,
      "in_records": 0,
      "out_bytes": 0,
      "out_records": 0,
      "shuf_r_bytes": 0,
      "shuf_r_records": 0,
      "shuf_w_bytes": 0,
      "shuf_w_records": 0,
  }

  stage_stats: Dict[Tuple[int, int], Dict[str, Any]] = {}
  seen_stage_partitions: Set[Tuple[int, int, int]] = set()
  accum_values: Dict[int, Any] = {}
  failed_accum_values: Dict[int, Any] = {}
  sql_executions: Dict[int, Dict[str, Any]] = {}
  connect_operations: Dict[str, Dict[str, Any]] = {}
  event_type_counts: Dict[str, int] = collections.defaultdict(int)

  line_count = 0

  def _stage_entry(s_id: int, s_att: int) -> Dict[str, Any]:
    key = (s_id, s_att)
    if key not in stage_stats:
      stage_stats[key] = {
          "stage_id": s_id,
          "attempt": s_att,
          "name": "",
          "status": "RUNNING",
          "num_tasks": 0,
          "completed_tasks": 0,
          "failed_tasks": 0,
          "submission_time": None,
          "completion_time": None,
          "in_bytes": 0,
          "in_records": 0,
          "out_bytes": 0,
          "out_records": 0,
          "shuf_r_bytes": 0,
          "shuf_r_records": 0,
          "shuf_w_bytes": 0,
          "shuf_w_records": 0,
          "mem_spill": 0,
          "disk_spill": 0,
          "task_durations_ms": [],
          "task_records": [],
      }
    return stage_stats[key]

  with contextlib.closing(reader.stream_lines()) as lines_gen:
    for line in lines_gen:
      line_count += 1
      line_str = line.strip()
      if not line_str or not line_str.startswith("{"):
        continue

      try:
        event = json.loads(line_str)
      except (json.JSONDecodeError, ValueError):
        continue

      event_type = event.get("Event")
      short_event = event_type.rsplit(".", 1)[-1] if event_type else ""
      if event_type:
        event_type_counts[event_type] += 1

      if short_event == "SparkListenerLogStart":
        spark_version = event.get("Spark Version", spark_version)
      elif short_event == "SparkListenerApplicationStart":
        app_id = event.get("App ID", app_id)
        app_name = event.get("App Name", app_name)
        spark_user = event.get("User", spark_user)
        start_time = event.get("Timestamp")
      elif short_event == "SparkListenerApplicationEnd":
        end_time = event.get("Timestamp")
      elif short_event == "SparkListenerJobStart":
        total_jobs += 1
      elif short_event == "SparkListenerJobEnd":
        job_result = event.get("Job Result", {})
        if job_result.get("Result") not in (None, "JobSucceeded"):
          failed_jobs += 1
      elif short_event == "SparkListenerStageSubmitted":
        total_stages += 1
        s_info = event.get("Stage Info") or {}
        s_id = int(s_info.get("Stage ID", -1))
        s_att = int(s_info.get("Stage Attempt ID", 0) or 0)
        if s_id >= 0:
          st = _stage_entry(s_id, s_att)
          st["name"] = s_info.get("Stage Name", st["name"])
          st["num_tasks"] = int(s_info.get("Number of Tasks", 0) or 0)
          st["submission_time"] = s_info.get("Submission Time")
      elif short_event == "SparkListenerStageCompleted":
        stage_info = event.get("Stage Info", {})
        s_id = int(stage_info.get("Stage ID", -1))
        s_att = int(stage_info.get("Stage Attempt ID", 0) or 0)
        s_name = stage_info.get("Stage Name", "")
        failure_reason = stage_info.get("Failure Reason")
        num_tasks = int(stage_info.get("Number of Tasks", 0) or 0)

        # Check metrics for spills and SQL accumulables; keep failed stage
        # accumulables separate so superseded attempts never inflate retries.
        accumulables = stage_info.get("Accumulables", [])
        target_accums = failed_accum_values if failure_reason else accum_values
        mem_spill = 0
        disk_spill = 0
        for acc in accumulables:
          acc_id = acc.get("ID")
          acc_val = acc.get("Value")
          if acc_id is not None and acc_val is not None:
            try:
              aid = int(acc_id)
              if (
                  isinstance(acc_val, str)
                  and acc_val.strip().lstrip("-").isdigit()
              ):
                acc_val = int(acc_val.strip())
              prev = target_accums.get(aid)
              if isinstance(acc_val, int) and isinstance(prev, int):
                target_accums[aid] = max(prev, acc_val)
              else:
                target_accums[aid] = acc_val
            except (TypeError, ValueError):
              pass
          acc_name = acc.get("Name", "")
          clean_acc = acc_name.lower().replace(" ", "").replace("_", "")
          if "memorybytesspilled" in clean_acc:
            mem_spill = int(acc.get("Value", 0) or 0)
          elif "diskbytesspilled" in clean_acc:
            disk_spill = int(acc.get("Value", 0) or 0)

        if s_id >= 0:
          st = _stage_entry(s_id, s_att)
          st["name"] = s_name or st["name"]
          st["num_tasks"] = num_tasks or st["num_tasks"]
          st["submission_time"] = (
              stage_info.get("Submission Time") or st["submission_time"]
          )
          st["completion_time"] = stage_info.get("Completion Time")
          st["status"] = "FAILED" if failure_reason else "COMPLETE"
          st["mem_spill"] = max(st["mem_spill"], mem_spill)
          st["disk_spill"] = max(st["disk_spill"], disk_spill)
        stage_exec_mem = stage_info.get("Task Executor Metrics") or {}
        if isinstance(stage_exec_mem, dict):
          for mkey in peak_task_exec_mem:
            mval = int(stage_exec_mem.get(mkey, 0) or 0)
            if mval > peak_task_exec_mem[mkey]:
              peak_task_exec_mem[mkey] = mval

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
      elif short_event == "SparkListenerTaskEnd":
        task_metrics = event.get("Task Metrics") or {}
        task_exec_mem = event.get("Task Executor Metrics") or {}
        if isinstance(task_exec_mem, dict):
          for mkey in peak_task_exec_mem:
            mval = int(task_exec_mem.get(mkey, 0) or 0)
            if mval > peak_task_exec_mem[mkey]:
              peak_task_exec_mem[mkey] = mval
        task_info = event.get("Task Info") or {}
        gc_ms = max(0, int(task_metrics.get("JVM GC Time", 0) or 0))
        run_ms = max(0, int(task_metrics.get("Executor Run Time", 0) or 0))
        total_gc_time += gc_ms
        task_end_reason = event.get("Task End Reason") or {}
        reason_type = task_end_reason.get("Reason")
        s_id = int(event.get("Stage ID", -1))
        s_att = int(event.get("Stage Attempt ID", 0) or 0)

        if reason_type and reason_type != "Success":
          if s_id >= 0:
            _stage_entry(s_id, s_att)["failed_tasks"] += 1
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
        else:
          task_idx = task_info.get("Index")
          if s_id >= 0 and task_idx is not None:
            part_key = (s_id, s_att, int(task_idx))
            if part_key in seen_stage_partitions:
              continue
            seen_stage_partitions.add(part_key)

          completed_tasks_count += 1
          completed_gc_time += gc_ms
          total_exec_run_time += run_ms
          in_m = task_metrics.get("Input Metrics") or {}
          out_m = task_metrics.get("Output Metrics") or {}
          sr_m = task_metrics.get("Shuffle Read Metrics") or {}
          sw_m = task_metrics.get("Shuffle Write Metrics") or {}
          in_b = max(0, int(in_m.get("Bytes Read", 0) or 0))
          in_r = max(0, int(in_m.get("Records Read", 0) or 0))
          out_b = max(0, int(out_m.get("Bytes Written", 0) or 0))
          out_r = max(0, int(out_m.get("Records Written", 0) or 0))
          sr_b = max(0, int(sr_m.get("Remote Bytes Read", 0) or 0)) + max(
              0, int(sr_m.get("Local Bytes Read", 0) or 0)
          )
          sr_r = max(0, int(sr_m.get("Total Records Read", 0) or 0))
          sw_b = max(0, int(sw_m.get("Shuffle Bytes Written", 0) or 0))
          sw_r = max(0, int(sw_m.get("Shuffle Records Written", 0) or 0))

          if s_id >= 0:
            st = _stage_entry(s_id, s_att)
            st["completed_tasks"] += 1
            st["in_bytes"] += in_b
            st["in_records"] += in_r
            st["out_bytes"] += out_b
            st["out_records"] += out_r
            st["shuf_r_bytes"] += sr_b
            st["shuf_r_records"] += sr_r
            st["shuf_w_bytes"] += sw_b
            st["shuf_w_records"] += sw_r
            launch = task_info.get("Launch Time")
            finish = task_info.get("Finish Time")
            if (
                isinstance(launch, int)
                and isinstance(finish, int)
                and finish >= launch
            ):
              dur = finish - launch
            else:
              dur = run_ms
            st["task_durations_ms"].append(dur)
            task_row_count = in_r or sr_r or out_r or sw_r
            st["task_records"].append(task_row_count)
          else:
            unattributed_io["in_bytes"] += in_b
            unattributed_io["in_records"] += in_r
            unattributed_io["out_bytes"] += out_b
            unattributed_io["out_records"] += out_r
            unattributed_io["shuf_r_bytes"] += sr_b
            unattributed_io["shuf_r_records"] += sr_r
            unattributed_io["shuf_w_bytes"] += sw_b
            unattributed_io["shuf_w_records"] += sw_r
      elif short_event == "SparkListenerExecutorAdded":
        executors_added += 1
        exec_info = event.get("Executor Info") or {}
        if isinstance(exec_info, dict):
          executor_cores_total += max(
              0, int(exec_info.get("Total Cores", 0) or 0)
          )
      elif short_event == "SparkListenerExecutorRemoved":
        executors_removed.append({
            "executor_id": event.get("Executor ID"),
            # Spark emits "Removed Reason" here, not "Reason". Reading the wrong
            # key made every executor loss report a reason of None -- exactly
            # the signal needed to distinguish OOM kills from preemption.
            "reason": event.get("Removed Reason"),
            "removed_time": event.get("Timestamp"),
            "line": line_count,
        })
      elif short_event in (
          "SparkListenerSQLExecutionStart",
          "SparkListenerSQLAdaptiveExecutionUpdate",
      ):
        exec_id = event.get("executionId")
        if exec_id is not None:
          eid = int(exec_id)
          rec = sql_executions.setdefault(
              eid,
              {
                  "execution_id": eid,
                  "description": "",
                  "start_time": None,
                  "end_time": None,
                  "physical_plan": "",
                  "spark_plan_info": None,
              },
          )
          if event.get("description"):
            rec["description"] = event["description"]
          if event.get("time") and rec["start_time"] is None:
            rec["start_time"] = event["time"]
          if event.get("physicalPlanDescription"):
            rec["physical_plan"] = event["physicalPlanDescription"]
          if event.get("sparkPlanInfo"):
            rec["spark_plan_info"] = event["sparkPlanInfo"]
      elif short_event == "SparkListenerSQLExecutionEnd":
        exec_id = event.get("executionId")
        if exec_id is not None:
          eid = int(exec_id)
          if eid in sql_executions:
            sql_executions[eid]["end_time"] = event.get("time")
      elif short_event.startswith("SparkListenerConnectOperation"):
        op_key = str(
            event.get("operationId")
            or event.get("jobTag")
            or f"line-{line_count}"
        )
        op_rec = connect_operations.setdefault(
            op_key,
            {
                "operation_id": event.get("operationId") or "",
                "job_tag": event.get("jobTag") or "",
                "session_id": event.get("sessionId") or "",
                "statement": "",
                "status": "STARTED",
                "start_time": None,
                "end_time": None,
                "produced_rows": None,
                "error_message": "",
            },
        )
        if event.get("jobTag"):
          op_rec["job_tag"] = event["jobTag"]
        if event.get("sessionId"):
          op_rec["session_id"] = event["sessionId"]
        stmt = event.get("statementText") or event.get("statement")
        if stmt:
          op_rec["statement"] = str(stmt)
        ev_ts = (
            event.get("eventTime")
            or event.get("startTime")
            or event.get("finishTime")
            or event.get("time")
        )
        if short_event == "SparkListenerConnectOperationStarted":
          if isinstance(ev_ts, int):
            op_rec["start_time"] = ev_ts
        elif short_event == "SparkListenerConnectOperationFinished":
          op_rec["status"] = "FINISHED"
          if isinstance(ev_ts, int):
            op_rec["end_time"] = ev_ts
          if event.get("producedRowCount") is not None:
            op_rec["produced_rows"] = event.get("producedRowCount")
        elif short_event == "SparkListenerConnectOperationFailed":
          op_rec["status"] = "FAILED"
          if isinstance(ev_ts, int):
            op_rec["end_time"] = ev_ts
          if event.get("errorMessage"):
            op_rec["error_message"] = str(event["errorMessage"])[:300]
        elif short_event == "SparkListenerConnectOperationCanceled":
          if op_rec["status"] != "FAILED":
            op_rec["status"] = "CANCELED"
          if isinstance(ev_ts, int) and op_rec["end_time"] is None:
            op_rec["end_time"] = ev_ts
        elif short_event == "SparkListenerConnectOperationClosed":
          if isinstance(ev_ts, int) and op_rec["end_time"] is None:
            op_rec["end_time"] = ev_ts
      elif short_event == "SparkListenerDriverAccumUpdates":
        for item in event.get("accumUpdates") or []:
          if isinstance(item, list) and len(item) >= 2:
            try:
              accum_values[int(item[0])] = item[1]
            except (TypeError, ValueError):
              pass
          elif isinstance(item, dict) and "ID" in item and "Value" in item:
            try:
              accum_values[int(item["ID"])] = item["Value"]
            except (TypeError, ValueError):
              pass

  for aid, aval in failed_accum_values.items():
    if aid not in accum_values:
      accum_values[aid] = aval

  attempts_by_stage: Dict[int, List[Dict[str, Any]]] = collections.defaultdict(
      list
  )
  for st in stage_stats.values():
    attempts_by_stage[st["stage_id"]].append(st)

  tot_in_bytes = unattributed_io["in_bytes"]
  tot_in_records = unattributed_io["in_records"]
  tot_out_bytes = unattributed_io["out_bytes"]
  tot_out_records = unattributed_io["out_records"]
  tot_shuf_r_bytes = unattributed_io["shuf_r_bytes"]
  tot_shuf_r_records = unattributed_io["shuf_r_records"]
  tot_shuf_w_bytes = unattributed_io["shuf_w_bytes"]
  tot_shuf_w_records = unattributed_io["shuf_w_records"]
  superseded_io = {
      "in_bytes": 0,
      "in_records": 0,
      "out_bytes": 0,
      "out_records": 0,
      "shuf_r_bytes": 0,
      "shuf_r_records": 0,
      "shuf_w_bytes": 0,
      "shuf_w_records": 0,
  }
  superseded_has_completed = False
  uncommitted_io = {
      "in_bytes": 0,
      "in_records": 0,
      "out_bytes": 0,
      "out_records": 0,
      "shuf_r_bytes": 0,
      "shuf_r_records": 0,
      "shuf_w_bytes": 0,
      "shuf_w_records": 0,
  }

  for _, st_list in sorted(attempts_by_stage.items()):
    st_list.sort(key=lambda item: item["attempt"])
    completed_attempts = [a for a in st_list if a["status"] == "COMPLETE"]
    if completed_attempts:
      chosen = completed_attempts[-1]
      tot_in_bytes += chosen["in_bytes"]
      tot_in_records += chosen["in_records"]
      tot_out_bytes += chosen["out_bytes"]
      tot_out_records += chosen["out_records"]
      tot_shuf_r_bytes += chosen["shuf_r_bytes"]
      tot_shuf_r_records += chosen["shuf_r_records"]
      tot_shuf_w_bytes += chosen["shuf_w_bytes"]
      tot_shuf_w_records += chosen["shuf_w_records"]
      for att in st_list:
        if att is not chosen:
          if att["status"] == "COMPLETE":
            superseded_has_completed = True
          for k in superseded_io:
            superseded_io[k] += att[k]
    else:
      for att in st_list:
        for k in uncommitted_io:
          uncommitted_io[k] += att[k]

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
  print(
      f"- **Tasks**: `{completed_tasks_count}` completed, `{len(failed_tasks)}`"
      " failed"
  )
  if executors_added > 0:
    print(
        f"- **Executors Added**: `{executors_added}`"
        f" (`{executor_cores_total}` total cores)"
    )
  if any(v > 0 for v in peak_task_exec_mem.values()):
    mem_parts = [
        "JVMHeap:"
        f" {spark_applications.human_bytes(peak_task_exec_mem['JVMHeapMemory'])}",
        "JVMOffHeap:"
        f" {spark_applications.human_bytes(peak_task_exec_mem['JVMOffHeapMemory'])}",
    ]
    if peak_task_exec_mem["ProcessTreeJVMRSSMemory"] > 0:
      mem_parts.append(
          "JVMRSS:"
          f" {spark_applications.human_bytes(peak_task_exec_mem['ProcessTreeJVMRSSMemory'])}"
      )
    if peak_task_exec_mem["ProcessTreePythonRSSMemory"] > 0:
      mem_parts.append(
          "PyRSS:"
          f" {spark_applications.human_bytes(peak_task_exec_mem['ProcessTreePythonRSSMemory'])}"
      )
    print(f"- **Peak Task Executor Memory**: {', '.join(mem_parts)}")
  print(f"- **Total JVM GC Time**: `{total_gc_time} ms`")
  print(f"- **Total Event Lines Processed**: `{line_count}`\n")

  print("### Workload & Ingestion I/O Totals (Completed Stages)")
  print(
      "- **Input**:"
      f" {spark_applications.human_io(tot_in_bytes, tot_in_records)}"
      f" (`{tot_in_bytes}` bytes, `{tot_in_records}` rows)"
  )
  print(
      f"- **Output**:"
      f" {spark_applications.human_io(tot_out_bytes, tot_out_records)}"
      f" (`{tot_out_bytes}` bytes, `{tot_out_records}` rows)"
  )
  print(
      f"- **Shuffle Read**:"
      f" {spark_applications.human_io(tot_shuf_r_bytes, tot_shuf_r_records)}"
  )
  print(
      f"- **Shuffle Write**:"
      f" {spark_applications.human_io(tot_shuf_w_bytes, tot_shuf_w_records)}"
  )
  has_superseded_non_in = any(
      superseded_io[k] > 0
      for k in (
          "out_bytes",
          "out_records",
          "shuf_r_bytes",
          "shuf_r_records",
          "shuf_w_bytes",
          "shuf_w_records",
      )
  )
  if any(v > 0 for v in superseded_io.values()):
    if not superseded_has_completed and not has_superseded_non_in:
      print(
          "- **Superseded Failed Attempt Input (excluded above)**:"
          f" {spark_applications.human_io(superseded_io['in_bytes'], superseded_io['in_records'])}"
      )
    else:
      sup_label = (
          "Superseded Stage Attempt I/O"
          if superseded_has_completed
          else "Superseded Failed Attempt I/O"
      )
      print(
          f"- **{sup_label} (excluded above)**: input"
          f" {spark_applications.human_io(superseded_io['in_bytes'], superseded_io['in_records'])},"
          " output"
          f" {spark_applications.human_io(superseded_io['out_bytes'], superseded_io['out_records'])},"
          " shuffle read"
          f" {spark_applications.human_io(superseded_io['shuf_r_bytes'], superseded_io['shuf_r_records'])},"
          " shuffle write"
          f" {spark_applications.human_io(superseded_io['shuf_w_bytes'], superseded_io['shuf_w_records'])}"
      )
  if any(v > 0 for v in uncommitted_io.values()):
    uncommitted_line = (
        "- **Uncommitted Failed/Incomplete Stage I/O (excluded above)**: input"
        f" {spark_applications.human_io(uncommitted_io['in_bytes'], uncommitted_io['in_records'])},"
        " output"
        f" {spark_applications.human_io(uncommitted_io['out_bytes'], uncommitted_io['out_records'])}"
    )
    if any(
        uncommitted_io[k] > 0
        for k in (
            "shuf_r_bytes",
            "shuf_r_records",
            "shuf_w_bytes",
            "shuf_w_records",
        )
    ):
      uncommitted_line += (
          ", shuffle read"
          f" {spark_applications.human_io(uncommitted_io['shuf_r_bytes'], uncommitted_io['shuf_r_records'])},"
          " shuffle write"
          f" {spark_applications.human_io(uncommitted_io['shuf_w_bytes'], uncommitted_io['shuf_w_records'])}"
      )
    print(uncommitted_line)
  gc_pct = (
      round(100.0 * completed_gc_time / total_exec_run_time, 2)
      if total_exec_run_time > 0
      else 0.0
  )
  print(
      f"- **Executor Run Time**: `{total_exec_run_time} ms` (GC overhead:"
      f" `{gc_pct}%`)\n"
  )

  if stage_stats:
    chosen_completed_keys: Set[Tuple[int, int]] = set()
    for _, st_list in attempts_by_stage.items():
      comp_atts = [a for a in st_list if a["status"] == "COMPLETE"]
      if comp_atts:
        last_c = comp_atts[-1]
        chosen_completed_keys.add((last_c["stage_id"], last_c["attempt"]))
    weighted_skew_sum = 0.0
    weighted_skew_dur = 0.0
    print(f"### Stage Breakdown ({len(stage_stats)} stages)")
    print(
        "| Stage | Status | Partitions (done/total) | Duration | Task Duration"
        " (med / max) | Partition Rows (med / max) | Input | Output | Shuffle"
        " R/W |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for key in sorted(stage_stats):
      st = stage_stats[key]
      sub_t, comp_t = st["submission_time"], st["completion_time"]
      st_dur = "n/a"
      st_dur_ms: Optional[int] = None
      if (
          isinstance(sub_t, int)
          and isinstance(comp_t, int)
          and comp_t >= sub_t
      ):
        st_dur_ms = comp_t - sub_t
        st_dur = spark_applications.human_millis(st_dur_ms)
      durs = st["task_durations_ms"]
      if durs:
        med_d = _median_int(durs)
        max_d = max(durs)
        skew_d = f"{max_d / med_d:.1f}x" if med_d > 0 else "n/a"
        s_score = spark_applications.compute_stage_skew_score(med_d, max_d)
        score_part = f", score={s_score:.2f}" if s_score is not None else ""
        dur_skew_str = (
            f"{spark_applications.human_millis(med_d)} /"
            f" {spark_applications.human_millis(max_d)}"
            f" ({skew_d}{score_part})"
        )
        if (
            key in chosen_completed_keys
            and s_score is not None
            and st_dur_ms is not None
            and st_dur_ms > 0
        ):
          weighted_skew_sum += float(st_dur_ms) * s_score
          weighted_skew_dur += float(st_dur_ms)
      else:
        dur_skew_str = "n/a"
      recs = st["task_records"]
      if recs and any(r > 0 for r in recs):
        med_r = _median_int(recs)
        max_r = max(recs)
        skew_r = f"{max_r / med_r:.1f}x" if med_r > 0 else "skewed"
        rec_skew_str = f"{int(round(med_r)):,} / {max_r:,} ({skew_r})"
      else:
        rec_skew_str = "n/a"
      total_part = st["num_tasks"] or (
          st["completed_tasks"] + st["failed_tasks"]
      )
      print(
          f"| {st['stage_id']}.{st['attempt']} | {st['status']} |"
          f" {st['completed_tasks']}/{total_part} | {st_dur} | {dur_skew_str}"
          f" | {rec_skew_str} |"
          f" {spark_applications.human_io(st['in_bytes'], st['in_records'])} |"
          f" {spark_applications.human_io(st['out_bytes'], st['out_records'])}"
          f" |"
          f" {spark_applications.human_io(st['shuf_r_bytes'], st['shuf_r_records'])}"
          f" /"
          f" {spark_applications.human_io(st['shuf_w_bytes'], st['shuf_w_records'])}"
          f" |"
      )
    if weighted_skew_dur > 0:
      job_skew = round(weighted_skew_sum / weighted_skew_dur, 2)
      print(f"\n- **Duration-weighted job_skew_score**: `{job_skew:.2f}`")
    print()

  if sql_executions:
    print(f"### SQL & Connector Executions ({len(sql_executions)})")
    for eid in sorted(sql_executions):
      sq = sql_executions[eid]
      s_t, e_t = sq["start_time"], sq["end_time"]
      sq_dur = (
          spark_applications.human_millis(e_t - s_t)
          if isinstance(s_t, int) and isinstance(e_t, int) and e_t >= s_t
          else "incomplete"
      )
      print(
          f"- **Execution {eid}** (`{sq['description'] or 'query'}`): duration"
          f" `{sq_dur}`"
      )
      for pnode in _walk_spark_plan_info(sq.get("spark_plan_info")):
        nname = (pnode.get("nodeName") or "").strip()
        if "WholeStageCodegen" in nname or nname == "AdaptiveSparkPlan":
          continue
        raw_node_nums: Dict[str, int] = {}
        node_metric_pairs: List[Tuple[str, str]] = []
        for m in pnode.get("metrics") or []:
          aid = m.get("accumulatorId")
          mname = m.get("name", "")
          mtype = m.get("metricType", "")
          if aid is not None and int(aid) in accum_values:
            raw_v = accum_values[int(aid)]
            if isinstance(raw_v, (int, float)):
              raw_node_nums[mname] = int(raw_v)
            elif (
                isinstance(raw_v, str)
                and raw_v.strip().lstrip("-").isdigit()
            ):
              raw_node_nums[mname] = int(raw_v.strip())
            fval = _format_sql_accum(raw_v, mtype)
            if fval:
              node_metric_pairs.append((mname, fval))
        rendered_metrics = []
        w_out = raw_node_nums.get("written output", 0)
        w_files = raw_node_nums.get("number of written files", 0)
        for mname, fval in node_metric_pairs:
          if (
              mname == "avg file size written"
              and w_out > 0
              and w_files > 1
              and raw_node_nums.get("avg file size written", 0)
              > (w_out / w_files) * 1.05
          ):
            true_avg = int(round(w_out / w_files))
            fval = (
                f"{fval} [true avg written output / files:"
                f" {spark_applications.human_bytes(true_avg)}]"
            )
          rendered_metrics.append(f"{mname}: {fval}")
        meta = pnode.get("metadata") or {}
        read_schema = meta.get("ReadSchema", "")
        col_note = ""
        if read_schema.startswith("struct<") and read_schema.endswith(">"):
          cols, num_cols, trunc = spark_applications._parse_col_items(  # pylint: disable=protected-access
              spark_applications._split_top_level_csv(  # pylint: disable=protected-access
                  read_schema[len("struct<") : -1]
              ),
              clean_expr=False,
          )
          preview = ", ".join(cols[:12])
          if len(cols) > 12 or trunc:
            preview += ", ..."
          col_note = f" [{num_cols} cols: {preview}]"
        if rendered_metrics or col_note:
          m_str = "; ".join(rendered_metrics)
          print(f"  - `{nname}`{col_note}: {m_str}")
      for op in spark_applications.extract_plan_schemas(
          sq.get("physical_plan", "")
      ):
        cols_preview = ", ".join(op["columns"][:12])
        if len(op["columns"]) > 12 or op.get("columns_truncated"):
          cols_preview += ", ..."
        print(
            f"  - Schema Node {op['node_id']} `{op['operator']}`:"
            f" `{op['num_columns']}` columns (`{cols_preview}`)"
        )
    print()

  if connect_operations:
    print(f"### Spark Connect & SDP Operations ({len(connect_operations)})")
    for op_key, op in connect_operations.items():
      s_t, e_t = op["start_time"], op["end_time"]
      op_dur = (
          spark_applications.human_millis(e_t - s_t)
          if isinstance(s_t, int) and isinstance(e_t, int) and e_t >= s_t
          else "incomplete"
      )
      label = op["operation_id"] or op_key
      tag_str = f", jobTag `{op['job_tag']}`" if op["job_tag"] else ""
      sess_str = f", session `{op['session_id']}`" if op["session_id"] else ""
      rows_str = (
          f", rows `{op['produced_rows']:,}`"
          if isinstance(op["produced_rows"], int)
          else ""
      )
      print(
          f"- **Operation `{label}`** ({op['status']}, duration `{op_dur}`"
          f"{tag_str}{sess_str}{rows_str})"
      )
      if op["statement"]:
        print(f"  - Statement: `{op['statement'][:200]}`")
      if op["error_message"]:
        print(f"  - Error: `{op['error_message']}`")
    print()

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


def main(argv: Optional[List[str]] = None):
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
      "--start-line",
      dest="start_line",
      type=int,
      default=1,
      help="Start line for read_range (1-indexed)",
  )
  parser.add_argument(
      "--end_line",
      "--end-line",
      dest="end_line",
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
      "--max-matches",
      dest="max_matches",
      type=int,
      default=20,
      help="Maximum search matches to print",
  )
  parser.add_argument(
      "--ignore_case",
      "--ignore-case",
      dest="ignore_case",
      action="store_true",
      help=(
          "Match --substring and --regex case-insensitively. Spark stack"
          " traces mix casing (Error/ERROR/error), so this is usually what you"
          " want when hunting for failures."
      ),
  )

  args = parser.parse_args(argv)
  reader = GcsStreamReader(args.uri)

  # `driverOutputResourceUri`, extensionless `application_<id>` URIs, and
  # rolling `eventlog_v2_application_<id>` directories resolve automatically.
  resolved_uris = reader.resolve_uris()
  if len(resolved_uris) > 1:
    print(
        f"Note: resolved rolling event log to {len(resolved_uris)} shards"
        f" ({resolved_uris[0]} .. {resolved_uris[-1]})",
        file=sys.stderr,
    )
    reader = GcsStreamReader(resolved_uris[0], shard_uris=resolved_uris)
  elif resolved_uris and resolved_uris[0] != args.uri:
    print(
        f"Note: resolved GCS log prefix to {resolved_uris[0]}", file=sys.stderr
    )
    reader = GcsStreamReader(resolved_uris[0])

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
      count = 0
      with contextlib.closing(reader.stream_lines()) as lines_gen:
        for line in lines_gen:
          sys.stdout.write(line)
          count += 1
          if count >= args.lines:
            break
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
