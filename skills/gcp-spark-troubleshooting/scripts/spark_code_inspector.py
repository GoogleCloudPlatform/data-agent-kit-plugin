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

"""Inspects remote Spark application source code, scripts, or archives from GCS.

Supports plain scripts (.py, .scala, .java, .sql) as well as JAR/ZIP archives
(.jar, .zip). For archives it can produce a structural overview (Main-Class,
package inventory, key entries) or extract and disassemble a specific entry.

Compiled JVM bytecode (.class) is never returned as raw bytes. It is
disassembled into readable JVM assembly using `javap` when a JDK is available,
and otherwise via a dependency-free pure-Python class file parser that recovers
the class declaration, fields, method signatures, string constants, and
referenced methods.
"""

import argparse
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import types
from typing import Dict, List, Optional, Sequence, Tuple
import zipfile

ARCHIVE_SUFFIXES = (".jar", ".zip")

GCS_URI_PREFIXES = (
    "gs://",
    "https://storage.googleapis.com/",
    "https://storage.cloud.google.com/",
)

# Maximum number of packages and key entries rendered in archive overview mode.
MAX_OVERVIEW_PACKAGES = 50
MAX_OVERVIEW_ENTRIES = 50

# Maximum number of companion inner classes disassembled alongside a target.
MAX_INNER_CLASSES = 10

# Minimum length for a constant pool string to be reported as a literal.
MIN_INTERESTING_STRING_LEN = 2

JVM_BASE_TYPES = types.MappingProxyType({
    "B": "byte",
    "C": "char",
    "D": "double",
    "F": "float",
    "I": "int",
    "J": "long",
    "S": "short",
    "Z": "boolean",
    "V": "void",
})

CLASS_ACCESS_FLAGS = (
    (0x0001, "public"),
    (0x0010, "final"),
    (0x0400, "abstract"),
    (0x4000, "enum"),
)

MEMBER_ACCESS_FLAGS = (
    (0x0001, "public"),
    (0x0002, "private"),
    (0x0004, "protected"),
    (0x0008, "static"),
    (0x0010, "final"),
    (0x0020, "synchronized"),
    (0x0040, "volatile"),
    (0x0080, "transient"),
    (0x0100, "native"),
    (0x0400, "abstract"),
)

ACC_INTERFACE = 0x0200

# Constant pool tags whose payload is a fixed number of bytes after the tag.
CONSTANT_TAG_SIZES = types.MappingProxyType({
    3: 4,  # Integer
    4: 4,  # Float
    5: 8,  # Long (occupies two slots)
    6: 8,  # Double (occupies two slots)
    7: 2,  # Class
    8: 2,  # String
    9: 4,  # Fieldref
    10: 4,  # Methodref
    11: 4,  # InterfaceMethodref
    12: 4,  # NameAndType
    15: 3,  # MethodHandle
    16: 2,  # MethodType
    17: 4,  # Dynamic
    18: 4,  # InvokeDynamic
    19: 2,  # Module
    20: 2,  # Package
})


def normalize_gcs_uri(uri: str) -> str:
  """Converts https storage URLs into canonical gs:// form."""
  for prefix in GCS_URI_PREFIXES[1:]:
    if uri.startswith(prefix):
      return "gs://" + uri[len(prefix) :]
  return uri


def is_gcs_uri(uri: str) -> bool:
  """Returns True when the URI points at Cloud Storage."""
  return uri.startswith(GCS_URI_PREFIXES)


def split_uri_fragment(uri: str) -> Tuple[str, Optional[str]]:
  """Splits 'gs://bucket/app.jar!/com/example/Main.class' into base and entry.

  Args:
    uri: A file URI that may carry an archive entry fragment after '!/'.

  Returns:
    A tuple of (base_uri, entry_path). entry_path is None when no fragment is
    present.
  """
  index = uri.find("!/")
  if index == -1:
    return uri, None
  entry = uri[index + 2 :].strip()
  return uri[:index], entry or None


def is_archive(uri: str) -> bool:
  """Returns True when the URI refers to a JAR or ZIP archive."""
  return uri.lower().endswith(ARCHIVE_SUFFIXES)


def download_to_local(uri: str, dest_dir: str) -> str:
  """Streams a GCS object to a local file, or returns an existing local path.

  Streaming to disk keeps memory usage flat, which matters for multi-hundred
  megabyte assembly JARs that would otherwise be buffered entirely in RAM.

  Args:
    uri: A gs:// URI, https storage URL, or local filesystem path.
    dest_dir: Directory used to store the downloaded object.

  Returns:
    Path of a readable local file.

  Raises:
    FileNotFoundError: If the URI cannot be resolved to a readable file.
  """
  if not is_gcs_uri(uri):
    if os.path.exists(uri):
      return uri
    raise FileNotFoundError(f"File not found: {uri}")

  canonical = normalize_gcs_uri(uri)
  local_path = os.path.join(dest_dir, os.path.basename(canonical) or "object")
  cmd = ["gcloud", "storage", "cp", canonical, local_path]
  try:
    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
  except subprocess.CalledProcessError as e:
    raise FileNotFoundError(
        f"Failed to download {canonical}: {(e.stderr or '').strip()}"
    ) from e
  if not os.path.exists(local_path):
    raise FileNotFoundError(f"Download produced no file for {canonical}")
  return local_path


def normalize_entry_path(entry_path: str) -> str:
  """Trims and normalizes separators in an archive entry path."""
  normalized = entry_path.strip().replace("\\", "/")
  return normalized.removeprefix("/")


def resolve_entry(zf: zipfile.ZipFile, entry_path: str) -> Optional[str]:
  """Resolves a user supplied entry path to an actual archive entry name.

  Accepts archive paths ('com/example/Main.class'), paths without the .class
  suffix, and fully-qualified dotted class names ('com.example.Main'), matching
  case-insensitively as a last resort.

  Args:
    zf: An open archive.
    entry_path: The requested entry, in any supported notation.

  Returns:
    The matching entry name, or None when no entry matches.
  """
  normalized = normalize_entry_path(entry_path)
  names = zf.namelist()
  name_set = frozenset(names)

  candidates = [normalized]
  if not normalized.endswith(".class"):
    candidates.append(normalized + ".class")
    candidates.append(normalized.replace(".", "/") + ".class")

  for candidate in candidates:
    if candidate in name_set:
      return candidate

  lowered = {name.lower(): name for name in names}
  for candidate in candidates:
    match = lowered.get(candidate.lower())
    if match:
      return match

  # Final fallback: match on the trailing path segment so that a bare class
  # name ('MySparkJob') resolves without the full package prefix.
  bare = candidates[0].rsplit("/", 1)[-1].removesuffix(".class").lower()
  for name in names:
    if name.lower().endswith(f"/{bare}.class"):
      return name
  return None


def find_inner_classes(zf: zipfile.ZipFile, entry_name: str) -> List[str]:
  """Finds companion inner class and closure entries for a target class.

  Scala and Java Spark jobs compile lambdas, closures, and companion objects
  into sibling '$' suffixed class files that carry the actual transformation
  logic, so they must be inspected alongside the requested class.

  Args:
    zf: An open archive.
    entry_name: The resolved entry name of the target class.

  Returns:
    A sorted list of companion class entry names.
  """
  if not entry_name.endswith(".class"):
    return []
  prefix = entry_name.removesuffix(".class") + "$"
  return sorted(
      name
      for name in zf.namelist()
      if name.startswith(prefix) and name.endswith(".class")
  )


def parse_field_descriptor(descriptor: str, index: int = 0) -> Tuple[str, int]:
  """Converts a JVM field descriptor into a readable type name.

  Args:
    descriptor: A JVM type descriptor such as '[Ljava/lang/String;'.
    index: Offset within the descriptor at which to begin parsing.

  Returns:
    A tuple of (readable type, index positioned after the parsed type).
  """
  array_depth = 0
  while index < len(descriptor) and descriptor[index] == "[":
    array_depth += 1
    index += 1
  if index >= len(descriptor):
    return "?" + "[]" * array_depth, index

  char = descriptor[index]
  if char == "L":
    end = descriptor.find(";", index)
    if end == -1:
      return "?" + "[]" * array_depth, len(descriptor)
    name = descriptor[index + 1 : end].replace("/", ".")
    index = end + 1
  elif char in JVM_BASE_TYPES:
    name = JVM_BASE_TYPES[char]
    index += 1
  else:
    name = "?"
    index += 1
  return name + "[]" * array_depth, index


def parse_method_descriptor(descriptor: str) -> Tuple[List[str], str]:
  """Splits a JVM method descriptor into parameter types and a return type."""
  if not descriptor.startswith("("):
    return [], parse_field_descriptor(descriptor)[0]
  end = descriptor.find(")")
  if end == -1:
    return [], "?"

  params = []
  index = 1
  while index < end:
    param, index = parse_field_descriptor(descriptor, index)
    params.append(param)
  return params, parse_field_descriptor(descriptor, end + 1)[0]


def decode_access_flags(flags: int, table: Sequence[Tuple[int, str]]) -> str:
  """Renders access flag bits as a space separated modifier string."""
  return " ".join(name for mask, name in table if flags & mask)


class JavaClassFile:
  """Minimal pure-Python parser for the JVM .class file format.

  Provides a dependency free fallback when no JDK `javap` binary is present,
  recovering the information needed for Spark root cause analysis: the class
  declaration, member signatures, embedded string literals (table names, GCS
  paths, SQL), and referenced methods.
  """

  def __init__(self, data: bytes):
    self._data = data
    self._pos = 0
    self.constants: Dict[int, Tuple[int, object]] = {}
    self.major_version = 0
    self.access_flags = 0
    self.this_class = ""
    self.super_class = ""
    self.interfaces: List[str] = []
    self.fields: List[Tuple[int, str, str]] = []
    self.methods: List[Tuple[int, str, str]] = []
    self._parse()

  def _read(self, size: int) -> bytes:
    if self._pos + size > len(self._data):
      raise ValueError("Truncated class file")
    chunk = self._data[self._pos : self._pos + size]
    self._pos += size
    return chunk

  def _u1(self) -> int:
    return self._read(1)[0]

  def _u2(self) -> int:
    return struct.unpack(">H", self._read(2))[0]

  def _u4(self) -> int:
    return struct.unpack(">I", self._read(4))[0]

  def _parse(self) -> None:
    """Parses the class file header, constant pool, fields, and methods."""
    if self._u4() != 0xCAFEBABE:
      raise ValueError("Not a Java class file (bad magic number)")
    self._u2()  # minor version
    self.major_version = self._u2()
    self._parse_constant_pool()

    self.access_flags = self._u2()
    self.this_class = self.class_name(self._u2())
    self.super_class = self.class_name(self._u2())

    for _ in range(self._u2()):
      self.interfaces.append(self.class_name(self._u2()))

    self.fields = self._parse_members()
    self.methods = self._parse_members()

  def _parse_constant_pool(self) -> None:
    """Reads the constant pool, tracking Utf8 values and structural refs."""
    count = self._u2()
    index = 1
    while index < count:
      tag = self._u1()
      if tag == 1:  # CONSTANT_Utf8
        length = self._u2()
        value = self._read(length).decode("utf-8", errors="replace")
        self.constants[index] = (tag, value)
      elif tag in CONSTANT_TAG_SIZES:
        payload = self._read(CONSTANT_TAG_SIZES[tag])
        self.constants[index] = (tag, payload)
      else:
        raise ValueError(f"Unsupported constant pool tag: {tag}")
      # Long and Double constants consume two constant pool slots.
      index += 2 if tag in (5, 6) else 1

  def _parse_members(self) -> List[Tuple[int, str, str]]:
    """Parses a field or method table into (flags, name, descriptor) tuples."""
    members = []
    for _ in range(self._u2()):
      flags = self._u2()
      name = self.utf8(self._u2())
      descriptor = self.utf8(self._u2())
      self._skip_attributes()
      members.append((flags, name, descriptor))
    return members

  def _skip_attributes(self) -> None:
    for _ in range(self._u2()):
      self._u2()  # attribute_name_index
      self._read(self._u4())

  def utf8(self, index: int) -> str:
    """Returns the Utf8 constant at the given index, or '?' when absent."""
    entry = self.constants.get(index)
    if entry and entry[0] == 1 and isinstance(entry[1], str):
      return entry[1]
    return "?"

  def class_name(self, index: int) -> str:
    """Resolves a CONSTANT_Class index to a dotted class name."""
    entry = self.constants.get(index)
    if not entry or entry[0] != 7 or not isinstance(entry[1], bytes):
      return ""
    name_index = struct.unpack(">H", entry[1])[0]
    return self.utf8(name_index).replace("/", ".")

  def string_literals(self) -> List[str]:
    """Returns embedded CONSTANT_String literals in constant pool order."""
    literals = []
    for _, (tag, payload) in sorted(self.constants.items()):
      if tag != 8 or not isinstance(payload, bytes):
        continue
      value = self.utf8(struct.unpack(">H", payload)[0])
      if len(value) >= MIN_INTERESTING_STRING_LEN:
        literals.append(value)
    return literals

  def method_references(self) -> List[str]:
    """Returns referenced methods as 'owner.name(descriptor)' strings."""
    references = []
    for _, (tag, payload) in sorted(self.constants.items()):
      if tag not in (10, 11) or not isinstance(payload, bytes):
        continue
      class_index, name_and_type_index = struct.unpack(">HH", payload)
      owner = self.class_name(class_index)
      name_and_type = self.constants.get(name_and_type_index)
      if not name_and_type or name_and_type[0] != 12:
        continue
      if not isinstance(name_and_type[1], bytes):
        continue
      name_index, descriptor_index = struct.unpack(">HH", name_and_type[1])
      name = self.utf8(name_index)
      descriptor = self.utf8(descriptor_index)
      references.append(f"{owner}.{name}{descriptor}")
    return references


def render_class_summary(data: bytes, entry_name: str) -> str:
  """Renders a readable structural summary of compiled JVM bytecode."""
  try:
    parsed = JavaClassFile(data)
  except (ValueError, struct.error, IndexError) as e:
    return f"// Failed to parse bytecode for {entry_name}: {e}"

  lines = [
      f"=== Class Structure: {entry_name} ===",
      f"Bytecode major version: {parsed.major_version}",
  ]

  modifiers = decode_access_flags(parsed.access_flags, CLASS_ACCESS_FLAGS)
  kind = "interface" if parsed.access_flags & ACC_INTERFACE else "class"
  declaration = " ".join(filter(None, [modifiers, kind, parsed.this_class]))
  if parsed.super_class and parsed.super_class != "java.lang.Object":
    declaration += f" extends {parsed.super_class}"
  if parsed.interfaces:
    declaration += " implements " + ", ".join(parsed.interfaces)
  lines.append("")
  lines.append(declaration + " {")

  for flags, name, descriptor in parsed.fields:
    field_type, _ = parse_field_descriptor(descriptor)
    field_modifiers = decode_access_flags(flags, MEMBER_ACCESS_FLAGS)
    lines.append(
        "  " + " ".join(filter(None, [field_modifiers, field_type, name])) + ";"
    )

  if parsed.fields and parsed.methods:
    lines.append("")

  for flags, name, descriptor in parsed.methods:
    params, return_type = parse_method_descriptor(descriptor)
    method_modifiers = decode_access_flags(flags, MEMBER_ACCESS_FLAGS)
    signature = f"{name}({', '.join(params)})"
    lines.append(
        "  "
        + " ".join(filter(None, [method_modifiers, return_type, signature]))
        + ";"
    )
  lines.append("}")

  literals = parsed.string_literals()
  if literals:
    lines.append("")
    lines.append("String constants (table names, paths, SQL, config keys):")
    for literal in literals:
      lines.append(f"  - {literal!r}")

  references = parsed.method_references()
  if references:
    lines.append("")
    lines.append("Referenced methods:")
    for reference in references:
      lines.append(f"  - {reference}")
  return "\n".join(lines)


def disassemble_with_javap(data: bytes, entry_name: str) -> Optional[str]:
  """Disassembles bytecode with `javap`, returning None when unavailable."""
  javap = shutil.which("javap")
  if not javap:
    return None

  with tempfile.TemporaryDirectory() as work_dir:
    # Preserve the package directory layout so javap accepts the class name.
    class_path = os.path.join(work_dir, entry_name)
    os.makedirs(os.path.dirname(class_path), exist_ok=True)
    with open(class_path, "wb") as f:
      f.write(data)
    try:
      result = subprocess.run(
          [javap, "-c", "-p", "-constants", class_path],
          check=False,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          text=True,
      )
    except (OSError, subprocess.SubprocessError):
      return None

  if result.returncode != 0 or not result.stdout.strip():
    return None
  return result.stdout


def disassemble_class(
    data: bytes, entry_name: str, use_javap: bool = True
) -> str:
  """Disassembles compiled bytecode into readable JVM assembly or structure."""
  if use_javap:
    output = disassemble_with_javap(data, entry_name)
    if output:
      return f"=== Disassembly (javap): {entry_name} ===\n{output}"
  return render_class_summary(data, entry_name)


def render_archive_overview(
    zf: zipfile.ZipFile, uri: str, total_size: int
) -> str:
  """Renders archive structure, Main-Class, and the package inventory."""
  lines = [f"=== JAR Archive Overview: {uri} ===", f"Size: {total_size} bytes"]

  main_class = None
  package_counts: Dict[str, int] = {}
  key_entries: List[str] = []
  total_entries = 0

  for info in zf.infolist():
    if info.is_dir():
      continue
    total_entries += 1
    name = info.filename

    if name == "META-INF/MANIFEST.MF":
      manifest = zf.read(name).decode("utf-8", errors="replace")
      for line in manifest.splitlines():
        if line.lower().startswith("main-class:"):
          main_class = line.split(":", 1)[1].strip()
          break

    if name.endswith(".class"):
      package = (
          name.rsplit("/", 1)[0].replace("/", ".")
          if "/" in name
          else "(default package)"
      )
      package_counts[package] = package_counts.get(package, 0) + 1

    if name.startswith("META-INF/") or "/" not in name:
      key_entries.append(name)

  lines.append("")
  if main_class:
    lines.append(f"Main-Class (from MANIFEST.MF): {main_class}")
  else:
    lines.append("Main-Class: Not specified in MANIFEST.MF")

  lines.append("")
  lines.append("Packages & Class Counts:")
  for index, package in enumerate(sorted(package_counts)):
    if index >= MAX_OVERVIEW_PACKAGES:
      lines.append(
          f"  ... (showing first {MAX_OVERVIEW_PACKAGES} packages out of"
          f" {len(package_counts)})"
      )
      break
    lines.append(f"  - {package} ({package_counts[package]} classes)")

  lines.append("")
  lines.append(f"Top-level / Key Entries (Total {total_entries} files):")
  for name in key_entries[:MAX_OVERVIEW_ENTRIES]:
    lines.append(f"  - {name}")

  lines.append("")
  lines.append(
      "To inspect or decompile a specific file/class, pass --entry (e.g."
      " 'com/example/Main.class' or 'com.example.Main') or append"
      " '!/path/to/file' to --uri."
  )
  return "\n".join(lines)


def render_numbered_text(content: str, max_lines: int) -> str:
  """Renders text content with line numbers and a truncation footer."""
  all_lines = content.splitlines()
  lines = [
      f"{i:4d} | {line}" for i, line in enumerate(all_lines[:max_lines], 1)
  ]
  if len(all_lines) > max_lines:
    lines.append(
        f"\n[Truncated at {max_lines} lines. Total lines: {len(all_lines)}]"
    )
  return "\n".join(lines)


def inspect_entry(
    zf: zipfile.ZipFile,
    uri: str,
    entry_path: str,
    max_lines: int,
    include_inner_classes: bool = True,
    use_javap: bool = True,
) -> str:
  """Extracts and renders a single archive entry.

  Plain-text entries are returned verbatim with line numbers. Compiled .class
  entries are disassembled, along with their companion inner classes.

  Args:
    zf: An open archive.
    uri: The archive URI, used for display only.
    entry_path: The requested entry, in any supported notation.
    max_lines: Maximum number of lines rendered for plain-text entries.
    include_inner_classes: Whether to also disassemble companion '$' classes.
    use_javap: Whether to attempt disassembly with the JDK `javap` tool.

  Returns:
    A rendered, human readable representation of the entry.
  """
  resolved = resolve_entry(zf, entry_path)
  if not resolved:
    return (
        f"Entry '{entry_path}' not found in JAR archive.\nUse --entry with an"
        " archive path ('com/example/Main.class') or a fully-qualified class"
        " name ('com.example.Main'). Omit --entry for an archive overview."
    )

  data = zf.read(resolved)
  if not resolved.endswith(".class"):
    header = f"=== Inspecting Entry '{resolved}' in {uri} ==="
    text = data.decode("utf-8", errors="replace")
    return f"{header}\n{render_numbered_text(text, max_lines)}"

  sections = [disassemble_class(data, resolved, use_javap=use_javap)]
  if include_inner_classes:
    inner_classes = find_inner_classes(zf, resolved)
    for inner in inner_classes[:MAX_INNER_CLASSES]:
      sections.append("")
      sections.append(
          disassemble_class(zf.read(inner), inner, use_javap=use_javap)
      )
    if len(inner_classes) > MAX_INNER_CLASSES:
      sections.append("")
      sections.append(
          f"[{len(inner_classes) - MAX_INNER_CLASSES} additional companion"
          " classes omitted. Pass --entry with the specific inner class name to"
          " inspect it.]"
      )
  return "\n".join(sections)


def inspect(
    uri: str,
    entry_path: Optional[str],
    max_lines: int,
    include_inner_classes: bool = True,
    use_javap: bool = True,
) -> str:
  """Inspects a Spark source file or archive and returns a rendered report.

  Args:
    uri: A gs:// URI, https storage URL, or local path. May contain a '!/'
      archive entry fragment.
    entry_path: Optional archive entry to extract; a '!/' fragment is used only
      when this is omitted.
    max_lines: Maximum number of lines rendered for plain-text content.
    include_inner_classes: Whether to also disassemble companion '$' classes.
    use_javap: Whether to attempt disassembly with the JDK `javap` tool.

  Returns:
    A rendered, human readable representation of the file or archive.

  Raises:
    FileNotFoundError: If the URI cannot be resolved to a readable file.
    ValueError: If entry selection is requested for a non-archive file.
  """
  base_uri, fragment_entry = split_uri_fragment(uri)
  target_entry = entry_path.strip() if entry_path else fragment_entry

  if not is_archive(base_uri):
    if target_entry:
      raise ValueError(
          "--entry and '!/' fragment syntax are only supported for .jar/.zip"
          f" archives, not for plain files like '{base_uri}'."
      )
    with tempfile.TemporaryDirectory() as work_dir:
      local_path = download_to_local(base_uri, work_dir)
      with open(local_path, "rb") as f:
        content = f.read().decode("utf-8", errors="replace")
    header = f"=== Source Code: {base_uri} ==="
    return f"{header}\n{render_numbered_text(content, max_lines)}"

  with tempfile.TemporaryDirectory() as work_dir:
    local_path = download_to_local(base_uri, work_dir)
    total_size = os.path.getsize(local_path)
    with zipfile.ZipFile(local_path) as zf:
      if not target_entry:
        return render_archive_overview(zf, base_uri, total_size)
      return inspect_entry(
          zf,
          base_uri,
          target_entry,
          max_lines,
          include_inner_classes=include_inner_classes,
          use_javap=use_javap,
      )


def main():
  parser = argparse.ArgumentParser(description="Remote Spark Code Inspector")
  parser.add_argument(
      "--uri",
      required=True,
      help=(
          "GCS URI (gs://...), https storage URL, or local file path. May"
          " include an archive entry fragment, e.g."
          " 'gs://bucket/app.jar!/com/example/Main.class'."
      ),
  )
  parser.add_argument(
      "--entry",
      help=(
          "Archive entry to inspect (for .jar or .zip). Accepts"
          " 'com/example/Main.class', 'com/example/Main', or"
          " 'com.example.Main'. Omit for an archive overview."
      ),
  )
  parser.add_argument(
      "--max_lines",
      type=int,
      default=300,
      help="Maximum lines of plain-text content to display",
  )
  parser.add_argument(
      "--no_inner_classes",
      action="store_true",
      help="Skip disassembly of companion inner classes and Scala closures",
  )
  parser.add_argument(
      "--no_javap",
      action="store_true",
      help=(
          "Skip JDK javap disassembly and always use the built-in pure-Python"
          " class parser"
      ),
  )

  args = parser.parse_args()

  try:
    print(
        inspect(
            args.uri,
            args.entry,
            args.max_lines,
            include_inner_classes=not args.no_inner_classes,
            use_javap=not args.no_javap,
        )
    )
  except (
      FileNotFoundError,
      ValueError,
      OSError,
      zipfile.BadZipFile,
      subprocess.SubprocessError,
  ) as e:
    print(f"Error inspecting {args.uri}: {e}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
