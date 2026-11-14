# Java Compatibility Analysis Guide

Java-specific checks: the Java release that the code compiles for, Java compiler
plugins, and Java code that uses Spark's Scala API. Use it with
`jvm_build_reference.md`, which covers what every Scala/Java job shares (the
job's jars, the Java runtime, the upgrade workflow, dependencies and packaging,
build checks, and the verification jar), and with
`spark_migration_reference.md`, which covers what every job type shares (version
mapping, component versions, the Java runtime, connectors, GPU/RAPIDS, and the
Spark migration notes; for Java jobs, the Core, SQL, Structured Streaming, and
MLlib notes apply, and the PySpark notes don't). A project that also has Scala
sources needs `scala_analysis.md` too.

This guide doesn't list what changed between Java versions, which would go
stale: the JDK Migration Guide describes the changes (`jvm_build_reference.md`,
section 2), and the target's compiler and JDK tools find the affected code.

## Procedure

1.  Take the source's and the target's Java and Scala versions from "Version to
    Spark Mapping" and the component pages (`spark_migration_reference.md`).
2.  Get the source and inspect the job's jars (`jvm_build_reference.md`, section
    1).
3.  Scan every `.java` file, the build definition, and the job's jars, Spark
    properties, and arguments:
    -   against the Spark migration notes, "Java Runtime", and "Connectors" in
        `spark_migration_reference.md`;
    -   for the Java runtime, the build changes, and the dependencies
        (`jvm_build_reference.md`, sections 2–4);
    -   for the Java release and compiler plugins (section 1), and for code that
        uses Spark's Scala API (section 2).
4.  Run the build checks (`jvm_build_reference.md`, section 5) with the compiler
    options in section 1.
5.  Record each finding with its `file:line`, why it breaks on the target, and
    the fix. The report format is in SKILL.md Step 3. The fixes are applied in
    Step 1.6, not during the analysis.

--------------------------------------------------------------------------------

## 1. Java Release and Compiler

-   **Java release.** Compile for the target's Java version with
    `--release <TARGET_JAVA>`: Maven's `maven.compiler.release` property or the
    compiler plugin's `<release>`
    (https://maven.apache.org/plugins/maven-compiler-plugin/examples/set-compiler-release.html),
    Gradle's `options.release` or a Java toolchain
    (https://docs.gradle.org/current/userguide/toolchains.html), or sbt's
    `javacOptions` in a mixed project. It replaces `-source` and `-target`
    (`maven.compiler.source` and `maven.compiler.target`, Gradle
    `sourceCompatibility` and `targetCompatibility`): unlike them, `--release`
    also compiles against that Java's API, so code that uses an API the target
    removed fails to compile.
    -   javac rejects `--release` if the build also exports packages of JDK
        modules (`--add-exports`), and JDK 8 `javac` does not support
        `--release` (added in JDK 9): when exporting JDK modules set `-source`
        and `-target` to `<TARGET_JAVA>` on a JDK of the target's version, and
        when building with JDK 8 `javac` use `-source 1.8 -target 1.8`
        (`maven.compiler.source` and `maven.compiler.target`).
    -   In the build-check copy, prefer `options.release` to a Gradle toolchain,
        which can download a JDK (`jvm_build_reference.md`, section 5, says not
        to install toolchains).
-   **Compiler warnings.** For the build checks, compile with
    `-Xlint:deprecation,removal` on JDK 9+ (or `-Xlint:deprecation` if running
    JDK 8 `javac`, which rejects `removal`; Maven `<compilerArgs>`, Gradle
    `options.compilerArgs`): uses of APIs that the target's Java or Spark
    deprecates are findings (SKILL.md rule 2).
-   **Annotation processors and compiler plugins** (e.g. Lombok, MapStruct, or
    Error Prone) depend on javac internals and need releases that support the
    JDK you build on: if the build fails inside one, upgrade it as its release
    notes describe. The build tool and its other plugins are covered in
    `jvm_build_reference.md`, section 5.

## 2. Java Code That Uses Spark's Scala API

Spark's core API is written in Scala. Java code that calls it directly handles
Scala types (`scala.collection.Seq`, `scala.Function1`, `scala.Tuple2`,
`scala.Option`, `scala.reflect.ClassTag`, or the converters between Java and
Scala collections), and depends on the Scala binary version just as Scala code
does:

-   Compile it against the Spark artifacts with the target's Scala suffix
    (`scala_analysis.md`, section 1): a jar compiled against another binary
    version fails with linkage errors.
-   If the binary version changes, check each use of a Scala type against the
    Scala changes (`scala_analysis.md`, section 2), such as where the collection
    converters live and which collection types Spark's methods accept and
    return.
-   Prefer Spark's Java API where one exists (`JavaSparkContext`, `JavaRDD`, the
    `org.apache.spark.api.java.function` interfaces, `Encoders`, and the
    Java-friendly overloads of `Dataset` methods): it keeps Scala types out of
    the job's code.
-   Changes to Spark's Java API itself are in the Spark migration notes
    (`spark_migration_reference.md`).
