# Scala Compatibility Analysis Guide

Scala-specific checks: the Scala version and binary compatibility, and the Scala
language, library, and compiler changes between the source's and the target's
Scala versions. Use it with `jvm_build_reference.md`, which covers what every
Scala/Java job shares (the job's jars, the Java runtime, the upgrade workflow,
dependencies and packaging, build checks, and the verification jar), and with
`spark_migration_reference.md`, which covers what every job type shares (version
mapping, component versions, the Java runtime, connectors, GPU/RAPIDS, and the
Spark migration notes; for Scala jobs, the Core, SQL, Structured Streaming, and
MLlib notes apply, and the PySpark notes don't). A project that also has Java
sources needs `java_analysis.md` too.

This guide doesn't list what changed between Scala versions, which would go
stale: it points to the official sources for the source and target versions, and
lets the target's compiler find the affected code.

## Procedure

1.  Take the source's and the target's Scala versions from "Version to Spark
    Mapping" and the component pages (`spark_migration_reference.md`). Record
    the full `<major>.<minor>.<patch>` version of each, not only its binary
    version (the `<major>.<minor>` part, e.g. `2.13`, which fails artifact
    resolution if placed directly in `scalaVersion` or `scala.version`). When a
    Serverless component page lists only the binary version, read the default
    `<scala.version>` of that binary track from the target Spark release's root
    `pom.xml`
    (`https://raw.githubusercontent.com/apache/spark/v<TARGET_SPARK>/pom.xml`),
    or pick a patch release on that binary track that supports `<TARGET_JAVA>`
    per the Scala JDK compatibility table (section 3).
2.  Get the source and inspect the job's jars (`jvm_build_reference.md`, section
    1).
3.  Scan every `.scala` file, the build definition, and the job's jars, Spark
    properties, and arguments:
    -   against the Spark migration notes, "Java Runtime", and "Connectors" in
        `spark_migration_reference.md`;
    -   for the Java runtime, the build changes, and the dependencies
        (`jvm_build_reference.md`, sections 2–4);
    -   for binary compatibility (section 1) and, if the binary version changes,
        the language and library changes (section 2).
4.  Check the toolchain (section 3), then run the build checks
    (`jvm_build_reference.md`, section 5) with the compiler options in
    section 3.
5.  Record each finding with its `file:line`, why it breaks on the target, and
    the fix. The report format is in SKILL.md Step 3. The fixes are applied in
    Step 1.6, not during the analysis.

--------------------------------------------------------------------------------

## 1. Scala Version and Binary Compatibility

-   **Binary versions don't mix.** Scala releases with different binary versions
    aren't binary compatible
    (https://docs.scala-lang.org/overviews/core/binary-compatibility-of-scala-releases.html):
    the job's classes and every Scala library it uses must be built for the
    target's binary version. This applies to Java jobs too, because they depend
    on Spark's Scala-suffixed artifacts (e.g. `spark-sql_<binary version>`). A
    mismatch fails at run time with linkage errors such as `NoSuchMethodError`
    or `NoClassDefFoundError` on `scala/` classes.
-   **Build with the target's exact Scala version.** Set `scalaVersion` (sbt),
    `scala.version` (Maven), or the `scala-library` version (Gradle) to the
    target's full Scala version, and check (L2) that no dependency pulls in a
    newer `scala-library`. Within a binary version, code compiled with an older
    release links with a newer one, but code compiled with a newer release than
    the target's isn't guaranteed to (see the binary compatibility policy).
-   **Artifact suffixes.** In sbt, `%%` appends the binary version of
    `scalaVersion` (`"org.apache.spark" %% "spark-sql" % sparkVersion`), but `%`
    with a hard-coded suffix
    (`"org.apache.spark" % "spark-sql-kafka-0-10_2.12" % sparkVersion`) doesn't:
    change the suffix. Maven and Gradle builds spell the suffix in each artifact
    ID, often through a property such as `scala.binary.version`. Change it for
    every Scala artifact (Spark modules and libraries), and in the job's own
    dependencies: `spark.jars.packages` (`--packages`) coordinates, and jars in
    `jarFileUris`, `spark.jars`, initialization actions, or custom images.
    Connectors follow "Connectors" in `spark_migration_reference.md` instead:
    remove their pins.
-   **Library releases.** Each third-party Scala library needs a release built
    for the target's binary version and Spark version, and libraries are
    sometimes renamed between releases: check the library's compatibility matrix
    or its published artifacts. If no release supports the target, report it as
    a blocker.

## 2. Scala Language and Library Changes

When the binary version changes, read the official sources for every binary
version after the source's, up to the target's (from 2.11 to 2.13, both 2.12 and
2.13):

-   the release notes of its first release,
    `https://github.com/scala/scala/releases/tag/v<binary version>.0` (e.g.
    `v2.13.0`), which describe its language, library, and compiler changes;
-   for 2.13, the collections migration guide
    (https://docs.scala-lang.org/overviews/core/collections-migration-213.html),
    which lists the changed collection APIs and their replacements.

Then let the target's compiler find the affected code: run L1
(`jvm_build_reference.md`, section 5) with the options in section 3. Each
compile error is a finding, and so is each deprecation warning, fixed as
SKILL.md rule 2 describes for deprecated APIs. The Scalafix migration rules of
scala-collection-compat (https://github.com/scala/scala-collection-compat)
rewrite many collection changes automatically; use them only if the project
already uses Scalafix or the user agrees, and review every rewrite against
rule 2.

Some Spark methods have both a Scala-function and a Java-interface overload
(e.g. `foreachPartition`). If a lambda passed to one stops compiling with a
misleading error, such as a missing member of `Object` or an ambiguous
reference, give the lambda's parameter type.

Behavior changes compile without errors. For each one that the sources describe,
check whether the code depends on it, especially where the job's output does
(e.g. a collection's string form or iteration order) and where Spark hands Scala
collections to the code (array and map values in a `Row`, or the result of
`collect`): the collection types that Spark returns follow the Scala version, so
read them through `Row`'s typed getters (e.g. `getSeq`) rather than casts.

## 3. Scala Toolchain

-   **Compiler options.** An option that the target's compiler doesn't accept
    fails with `bad option`: remove or replace it in `scalacOptions` or in the
    Maven or Gradle compiler arguments, as the release notes (section 2)
    describe. For the build checks, add `-deprecation` and
    `-Xmigration:<source binary version>`, which warns about code whose behavior
    may have changed since that version
    (https://docs.scala-lang.org/overviews/compiler-options/index.html). If the
    build sets a Java target (`-release` or `-target:`), set `-release` to
    `<TARGET_JAVA>` on Scala 2.13 and later; when targeting Scala 2.12 (which
    only emits Java 8 bytecode even on Java 11 or 17 runtimes), keep
    `-release 8` (or `-target:jvm-1.8`).
-   **Compiler and build tool versus the JDK.** The Scala compiler and sbt each
    need a release that supports the JDK you build on; the minimum versions for
    each JDK are at
    https://docs.scala-lang.org/overviews/jdk-compatibility/overview.html (sbt's
    version is in `project/build.properties`). Build plugins
    (`scala-maven-plugin`, `sbt-assembly`, the Gradle Scala plugin) need
    releases that support the target's Scala version and the JDK.
