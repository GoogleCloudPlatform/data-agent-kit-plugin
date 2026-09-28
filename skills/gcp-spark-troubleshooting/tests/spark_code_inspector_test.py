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

"""Unit tests for spark_code_inspector."""

import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
)
# pylint: disable=g-import-not-at-top
import spark_code_inspector

JAVA_SOURCE = """package com.example;

public class SparkJob {
  private int retries;

  public static void main(String[] args) {
    System.out.println("gs://my-bucket/input/data.parquet");
  }

  public int add(int a, int b) {
    return a + b;
  }
}
"""

INNER_CLASS_SOURCE = """package com.example;

public class WithClosure {
  public Runnable makeClosure() {
    return new Runnable() {
      @Override
      public void run() {
        System.out.println("closure body");
      }
    };
  }
}
"""

MANIFEST = "Manifest-Version: 1.0\nMain-Class: com.example.SparkJob\n\n"


def compile_java(source: str, class_name: str, work_dir: str) -> str:
  """Compiles Java source and returns the output directory root.

  Args:
    source: Java source text.
    class_name: Simple class name matching the public class in the source.
    work_dir: Directory used for source and compiler output.

  Returns:
    The directory containing the compiled package tree.
  """
  source_path = os.path.join(work_dir, f"{class_name}.java")
  with open(source_path, "w") as f:
    f.write(source)
  subprocess.run(
      ["javac", "-d", work_dir, source_path],
      check=True,
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
  )
  return work_dir


class UriParsingTest(unittest.TestCase):

  def test_split_uri_fragment_without_fragment(self):
    self.assertEqual(
        spark_code_inspector.split_uri_fragment("gs://bucket/app.jar"),
        ("gs://bucket/app.jar", None),
    )

  def test_split_uri_fragment_with_fragment(self):
    self.assertEqual(
        spark_code_inspector.split_uri_fragment(
            "gs://bucket/app.jar!/com/example/Main.class"
        ),
        ("gs://bucket/app.jar", "com/example/Main.class"),
    )

  def test_normalize_https_storage_url(self):
    self.assertEqual(
        spark_code_inspector.normalize_gcs_uri(
            "https://storage.googleapis.com/bucket/app.jar"
        ),
        "gs://bucket/app.jar",
    )

  def test_is_archive(self):
    self.assertTrue(spark_code_inspector.is_archive("gs://b/app.JAR"))
    self.assertTrue(spark_code_inspector.is_archive("gs://b/app.zip"))
    self.assertFalse(spark_code_inspector.is_archive("gs://b/job.py"))

  def test_normalize_entry_path_strips_leading_slash(self):
    self.assertEqual(
        spark_code_inspector.normalize_entry_path("/com\\example\\Main.class"),
        "com/example/Main.class",
    )


class DescriptorParsingTest(unittest.TestCase):

  def test_parse_field_descriptor_primitive(self):
    self.assertEqual(spark_code_inspector.parse_field_descriptor("I")[0], "int")

  def test_parse_field_descriptor_object_array(self):
    self.assertEqual(
        spark_code_inspector.parse_field_descriptor("[Ljava/lang/String;")[0],
        "java.lang.String[]",
    )

  def test_parse_method_descriptor(self):
    params, return_type = spark_code_inspector.parse_method_descriptor(
        "(Ljava/lang/String;I)Z"
    )
    self.assertEqual(params, ["java.lang.String", "int"])
    self.assertEqual(return_type, "boolean")

  def test_parse_method_descriptor_void_no_args(self):
    params, return_type = spark_code_inspector.parse_method_descriptor("()V")
    self.assertEqual(params, [])
    self.assertEqual(return_type, "void")


class EntryResolutionTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.temp_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.temp_dir)
    self.jar_path = os.path.join(self.temp_dir, "app.jar")
    with zipfile.ZipFile(self.jar_path, "w") as zf:
      zf.writestr("META-INF/MANIFEST.MF", MANIFEST)
      zf.writestr("com/example/SparkJob.class", b"\xca\xfe\xba\xbe")
      zf.writestr("com/example/SparkJob$1.class", b"\xca\xfe\xba\xbe")
      zf.writestr("com/example/SparkJob$Helper.class", b"\xca\xfe\xba\xbe")
      zf.writestr("config/spark.properties", "spark.executor.memory=4g\n")

  def test_resolve_exact_archive_path(self):
    with zipfile.ZipFile(self.jar_path) as zf:
      self.assertEqual(
          spark_code_inspector.resolve_entry(zf, "com/example/SparkJob.class"),
          "com/example/SparkJob.class",
      )

  def test_resolve_dotted_class_name(self):
    with zipfile.ZipFile(self.jar_path) as zf:
      self.assertEqual(
          spark_code_inspector.resolve_entry(zf, "com.example.SparkJob"),
          "com/example/SparkJob.class",
      )

  def test_resolve_path_without_class_suffix(self):
    with zipfile.ZipFile(self.jar_path) as zf:
      self.assertEqual(
          spark_code_inspector.resolve_entry(zf, "com/example/SparkJob"),
          "com/example/SparkJob.class",
      )

  def test_resolve_bare_class_name(self):
    with zipfile.ZipFile(self.jar_path) as zf:
      self.assertEqual(
          spark_code_inspector.resolve_entry(zf, "SparkJob"),
          "com/example/SparkJob.class",
      )

  def test_resolve_missing_entry_returns_none(self):
    with zipfile.ZipFile(self.jar_path) as zf:
      self.assertIsNone(
          spark_code_inspector.resolve_entry(zf, "com.example.Missing")
      )

  def test_find_inner_classes(self):
    with zipfile.ZipFile(self.jar_path) as zf:
      self.assertEqual(
          spark_code_inspector.find_inner_classes(
              zf, "com/example/SparkJob.class"
          ),
          [
              "com/example/SparkJob$1.class",
              "com/example/SparkJob$Helper.class",
          ],
      )

  def test_find_inner_classes_for_non_class_entry(self):
    with zipfile.ZipFile(self.jar_path) as zf:
      self.assertEqual(
          spark_code_inspector.find_inner_classes(
              zf, "config/spark.properties"
          ),
          [],
      )


class ArchiveOverviewTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.temp_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.temp_dir)
    self.jar_path = os.path.join(self.temp_dir, "app.jar")
    with zipfile.ZipFile(self.jar_path, "w") as zf:
      zf.writestr("META-INF/MANIFEST.MF", MANIFEST)
      zf.writestr("com/example/SparkJob.class", b"\xca\xfe\xba\xbe")
      zf.writestr("com/example/Helper.class", b"\xca\xfe\xba\xbe")
      zf.writestr("com/example/util/Io.class", b"\xca\xfe\xba\xbe")

  def test_overview_reports_main_class_and_packages(self):
    result = spark_code_inspector.inspect(self.jar_path, None, 300)
    self.assertIn("JAR Archive Overview", result)
    self.assertIn("Main-Class (from MANIFEST.MF): com.example.SparkJob", result)
    self.assertIn("com.example (2 classes)", result)
    self.assertIn("com.example.util (1 classes)", result)
    self.assertIn("META-INF/MANIFEST.MF", result)

  def test_missing_entry_returns_helpful_message(self):
    result = spark_code_inspector.inspect(
        self.jar_path, "com.example.Missing", 300
    )
    self.assertIn("not found in JAR archive", result)

  def test_plain_text_entry_returned_verbatim(self):
    jar_path = os.path.join(self.temp_dir, "text.jar")
    with zipfile.ZipFile(jar_path, "w") as zf:
      zf.writestr("conf/app.properties", "spark.sql.shuffle.partitions=200\n")
    result = spark_code_inspector.inspect(jar_path, "conf/app.properties", 300)
    self.assertIn("spark.sql.shuffle.partitions=200", result)

  def test_entry_path_rejected_for_plain_files(self):
    script_path = os.path.join(self.temp_dir, "job.py")
    with open(script_path, "w") as f:
      f.write("print('hello')\n")
    with self.assertRaises(ValueError):
      spark_code_inspector.inspect(script_path, "main.py", 300)

  def test_plain_script_is_line_numbered(self):
    script_path = os.path.join(self.temp_dir, "job.py")
    with open(script_path, "w") as f:
      f.write("import pyspark\nprint('hello')\n")
    result = spark_code_inspector.inspect(script_path, None, 300)
    self.assertIn("   1 | import pyspark", result)
    self.assertIn("   2 | print('hello')", result)

  def test_plain_script_truncates_at_max_lines(self):
    script_path = os.path.join(self.temp_dir, "long.py")
    with open(script_path, "w") as f:
      f.write("\n".join(f"line{i}" for i in range(50)))
    result = spark_code_inspector.inspect(script_path, None, 10)
    self.assertIn("[Truncated at 10 lines. Total lines: 50]", result)


class ClassFileParsingTest(unittest.TestCase):
  """Validates bytecode parsing against real javac output."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls.has_javac = shutil.which("javac") is not None

  def setUp(self):
    super().setUp()
    if not self.has_javac:
      self.skipTest("javac is unavailable in this environment")
    self.temp_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.temp_dir)

  def build_jar(self, sources, jar_name="app.jar"):
    """Compiles sources and packages the resulting classes into a jar."""
    build_dir = os.path.join(self.temp_dir, "build")
    os.makedirs(build_dir, exist_ok=True)
    for class_name, source in sources:
      compile_java(source, class_name, build_dir)

    jar_path = os.path.join(self.temp_dir, jar_name)
    with zipfile.ZipFile(jar_path, "w") as zf:
      zf.writestr("META-INF/MANIFEST.MF", MANIFEST)
      for root, _, files in os.walk(build_dir):
        for name in files:
          if not name.endswith(".class"):
            continue
          full_path = os.path.join(root, name)
          zf.write(full_path, os.path.relpath(full_path, build_dir))
    return jar_path

  def test_pure_python_parser_recovers_class_structure(self):
    jar_path = self.build_jar([("SparkJob", JAVA_SOURCE)])
    result = spark_code_inspector.inspect(
        jar_path, "com.example.SparkJob", 300, use_javap=False
    )
    self.assertIn("public class com.example.SparkJob", result)
    self.assertIn("int retries", result)
    self.assertIn("main(java.lang.String[])", result)
    self.assertIn("add(int, int)", result)

  def test_pure_python_parser_extracts_string_literals(self):
    jar_path = self.build_jar([("SparkJob", JAVA_SOURCE)])
    result = spark_code_inspector.inspect(
        jar_path, "com.example.SparkJob", 300, use_javap=False
    )
    self.assertIn("gs://my-bucket/input/data.parquet", result)

  def test_pure_python_parser_lists_referenced_methods(self):
    jar_path = self.build_jar([("SparkJob", JAVA_SOURCE)])
    result = spark_code_inspector.inspect(
        jar_path, "com.example.SparkJob", 300, use_javap=False
    )
    self.assertIn("java.io.PrintStream.println", result)

  def test_javap_disassembly_emits_opcodes(self):
    if not shutil.which("javap"):
      self.skipTest("javap is unavailable in this environment")
    jar_path = self.build_jar([("SparkJob", JAVA_SOURCE)])
    result = spark_code_inspector.inspect(jar_path, "com.example.SparkJob", 300)
    self.assertIn("Disassembly (javap)", result)
    self.assertIn("invokevirtual", result)

  def test_bytecode_is_never_returned_as_raw_utf8(self):
    jar_path = self.build_jar([("SparkJob", JAVA_SOURCE)])
    result = spark_code_inspector.inspect(
        jar_path, "com.example.SparkJob", 300, use_javap=False
    )
    self.assertNotIn("\ufffd", result)

  def test_inner_classes_are_disassembled(self):
    jar_path = self.build_jar(
        [("WithClosure", INNER_CLASS_SOURCE)], jar_name="closure.jar"
    )
    result = spark_code_inspector.inspect(
        jar_path, "com.example.WithClosure", 300, use_javap=False
    )
    self.assertIn("com.example.WithClosure", result)
    self.assertIn("WithClosure$1.class", result)
    self.assertIn("closure body", result)

  def test_inner_classes_can_be_skipped(self):
    jar_path = self.build_jar(
        [("WithClosure", INNER_CLASS_SOURCE)], jar_name="closure.jar"
    )
    result = spark_code_inspector.inspect(
        jar_path,
        "com.example.WithClosure",
        300,
        include_inner_classes=False,
        use_javap=False,
    )
    self.assertNotIn("WithClosure$1.class", result)

  def test_uri_fragment_selects_entry(self):
    jar_path = self.build_jar([("SparkJob", JAVA_SOURCE)])
    result = spark_code_inspector.inspect(
        f"{jar_path}!/com/example/SparkJob.class", None, 300, use_javap=False
    )
    self.assertIn("public class com.example.SparkJob", result)


class MalformedBytecodeTest(unittest.TestCase):

  def test_invalid_magic_number_reports_error(self):
    result = spark_code_inspector.render_class_summary(
        b"\x00\x00\x00\x00", "Bad.class"
    )
    self.assertIn("Failed to parse bytecode", result)

  def test_truncated_class_file_reports_error(self):
    data = struct.pack(">IHH", 0xCAFEBABE, 0, 65)
    result = spark_code_inspector.render_class_summary(data, "Truncated.class")
    self.assertIn("Failed to parse bytecode", result)


if __name__ == "__main__":
  unittest.main()
