# JVM Build Reference (Scala/Java)

What every Scala/Java job shares, whatever its source language: the source
behind its jars, the Java runtime of its code and libraries, the upgrade
workflow for its build definition, its dependencies and packaging, the build
checks against the target, and the jar for verification and delivery. The
language-specific checks are in `scala_analysis.md` (Scala sources) and
`java_analysis.md` (Java sources), which say when to use each section here. What
every job type shares (version mapping, component versions, the Java runtime,
connectors, GPU/RAPIDS, and the Spark migration notes) is in
`spark_migration_reference.md`.

--------------------------------------------------------------------------------

## 1. Source Code, Jars, and the Build Definition

A Scala/Java job runs compiled code: the `mainJarFileUri` of its `sparkJob`
(clusters) or `sparkBatch` (Serverless), or a `mainClass` loaded from one of its
`jarFileUris`.

-   **A jar isn't source code.** The upgrade edits the source and rebuilds the
    jar, so it needs the source tree and its build definition: sbt (`build.sbt`,
    `project/build.properties`, `project/plugins.sbt`), Maven (`pom.xml`), or
    Gradle (`build.gradle` or `build.gradle.kts`, and `settings.gradle`). If the
    user gave only a jar, ask for the source (a Git URL or local path). Without
    it, inspect the jar as described below and report that the code can't be
    upgraded: a jar built for a different Scala binary version than the target's
    (`scala_analysis.md`, section 1) can't run on the target at all.
-   **Source languages.** `.scala` files need `scala_analysis.md`, and `.java`
    files need `java_analysis.md`; a project with both needs both.
-   **Jars from the image.** If the main class comes from a jar that the image
    provides (a `file:///usr/lib/...` URI, such as the Spark examples jar),
    there is no user code to upgrade: check only the job's arguments,
    properties, and other jars.
-   **`<app_id>`** (SKILL.md Terminology): use the main jar's file name, or the
    main class's simple name when the job sets only `mainClass` (e.g.
    `com.example.OrderMetricsApp` → `ordermetricsapp`).
-   **Inspect the jars:** the main jar when there's no source, and every jar
    that the job adds (`jarFileUris`, `spark.jars`) in any case.
    -   Bundled classes: `jar tf <JAR>` (or `unzip -l <JAR>`). Entries under
        `scala/`, `org/apache/spark/`, or `org/apache/hadoop/` mean that the jar
        bundles libraries the platform provides (section 4). Each
        `META-INF/maven/<groupId>/<artifactId>/pom.properties` entry names a
        bundled Maven artifact and its version; an artifact ID's suffix (e.g.
        `_2.12`) is its Scala binary version.
    -   Java version:
        `javap -v -cp <JAR> <fully.qualified.ClassName> | grep major` prints the
        class-file version, which is the Java version plus 44 (52 is Java 8, 65
        is Java 21). Classes compiled for a newer Java than the target's fail
        with `UnsupportedClassVersionError`.
    -   Scala version, if the jar has no Maven metadata: the Scala library
        classes that its bytecode references (`javap -c -p` on a few classes)
        identify it. Bytecode compiled for Scala 2.13 references
        `scala/collection/IterableOnce`, and bytecode compiled for 2.12 or
        earlier references `scala/collection/TraversableOnce`.

## 2. Java Runtime

Code compiled for an older Java runs on a newer one, unless the code or a
library it uses relies on a JDK API, internal, or behavior that changed in
between. The JDK Migration Guide of the target's Java version ("Official
sources" in `spark_migration_reference.md`) describes the changes: read the
releases after the source's Java version, and for a source on Java 8, also the
guide's chapter on migrating from JDK 8. When the Java version changes, the
build checks (section 5) find most affected code:

-   compiling for the target's Java release (L1, with the compiler options in
    `java_analysis.md` or `scala_analysis.md`) fails on JDK APIs that the target
    no longer has;
-   `jdeprscan` and `jdeps` (L3) list uses of APIs deprecated for removal and of
    JDK internals, in the job's code and in the libraries its jar bundles;
-   behavior changes compile cleanly: check the code for the ones that the guide
    describes (e.g. in default character sets, locale data, or security
    defaults), and run the tests (L4).

Reflective access to JDK internals that the target encapsulates fails at run
time with `InaccessibleObjectException`
(`module java.base does not "opens java.lang" to unnamed module`). Upgrade the
library or change the code; if neither is possible, add
`--add-opens=<module>/<package>=ALL-UNNAMED` to `spark.driver.extraJavaOptions`
and `spark.executor.extraJavaOptions`. Spark adds the options that it needs for
itself. Record every JVM option or system property that restores an older JDK
behavior, `--add-opens` included, like a legacy flag (SKILL.md rule 2). JVM
options that the target's Java rejects are covered by "Java Runtime" in
`spark_migration_reference.md`.

## 3. Upgrade Workflow

These are the changes that point the build at the target. In Step 1.5, apply
step 1 only to the build-check copy (section 5), and record what each step needs
as planned changes; apply them to the working copy in Step 1.6, after checkpoint
1 (SKILL.md rule 5), then re-run the build checks.

1.  **Static POM/sbt scan: point the build at the target.** Set the Spark
    version (`spark.version`), the Scala binary and full
    `<major>.<minor>.<patch>` versions (Maven `scala.binary.version` and
    `scala.version`, sbt `scalaVersion`—if the component page lists only the
    binary version, resolve the patch version as `scala_analysis.md`, Procedure
    step 1 describes), and the Java release to the target's versions from its
    component page. Maven builds usually keep them in `<properties>`, Gradle
    builds in `gradle.properties` or the build script, and sbt builds in
    `build.sbt`; versions can also come from a parent POM or an imported BOM
    (`<dependencyManagement>`), a Gradle version catalog
    (`gradle/libs.versions.toml`), or sbt files under `project/` (and
    `crossScalaVersions`). The compiler options for the Java release are in
    `java_analysis.md` and `scala_analysis.md`.
2.  **Audit the dependency tree.** Print the resolved dependencies and check
    that every artifact that the platform provides is `provided`, that every
    Scala artifact has the target's suffix (`scala_analysis.md`, section 1), and
    that the libraries the job bundles don't collide with the platform's
    (section 4):
    -   Maven: `mvn dependency:tree` shows each artifact's scope.
    -   Gradle: `gradle dependencies --configuration runtimeClasspath` must not
        list the platform's artifacts (`compileOnly` keeps them out).
    -   sbt: `show Runtime/fullClasspath` (what an assembly jar bundles) must
        not list them, and `show Compile/dependencyClasspath` shows their
        resolved versions; both work without extra plugins. `dependencyTree`
        (sbt 1.4+, when `addDependencyTreePlugin` is enabled in
        `project/plugins.sbt` in the `build_<app_id>_temp/` copy; sbt `< 1.4`
        needs `sbt-dependency-graph`) shows which dependency pulls in each
        bundled library, but leaves out `provided` dependencies and, by default,
        `scala-library`.
3.  **Remove outdated system hooks.** Look for initialization actions, custom
    image steps, and deployment scripts that copy jars into Spark's system
    directories, such as `/usr/lib/spark/jars/`, to add the job's dependencies,
    override a connector, or replace a library that Spark ships. Such jars
    bypass the build's dependency management, can collide with the target's own
    jars, and pollute the classpath of the Managed Spark agent, which can cause
    job cancellation failures and orphaned YARN applications
    (https://docs.cloud.google.com/managed-spark/docs/guides/manage-spark-dependencies).
    Remove those steps, and supply what they supplied the supported way:

    -   the job's dependencies: bundled in its jar, or passed with the job
        (`jarFileUris` or `--jars`, `spark.jars.packages`). For jars that every
        job on a cluster needs, use the `spark:spark.jars` cluster property; a
        job that passes its own jars replaces that property's list rather than
        adding to it, so include those jars in the job's list too.
    -   a connector: the platform's own, or its override ("Connectors" in
        `spark_migration_reference.md`).
    -   a replaced Spark library: shade the job's version (section 4). A jar
        passed with the job doesn't override Spark's copy.

    Leave the hooks out of the Step 2 cluster too, and list each removal in the
    report's production configuration. On Serverless, a custom container that
    adds jars to the classpath (through `SPARK_EXTRA_CLASSPATH`) must be rebuilt
    for the target runtime, with jars built for the target's Spark and Scala
    versions.

## 4. Dependencies and Packaging

-   **Use `provided` scope for what the platform provides.** The image or
    runtime provides Spark, the Scala library, Hadoop, the connectors in
    "Connectors" (`spark_migration_reference.md`), and on clusters the optional
    components that the cluster enables (e.g. Delta Lake or Iceberg; versions on
    the component page). Declare the ones the code compiles against at the
    target's versions with `provided` scope (sbt `% "provided"`, Maven
    `<scope>provided</scope>`, Gradle `compileOnly`): they stay on the compile
    classpath but out of the assembly ("fat") jar, where a copy at another
    version would collide with the platform's (`NoSuchMethodError`,
    `ClassCastException`, `IncompatibleClassChangeError`).
    -   sbt-assembly bundles the Scala library unless told not to
        (`assemblyPackageScala / assembleArtifact := false`).
    -   Don't bundle logging backends or bindings (Log4j implementations, SLF4J
        bindings, Logback): the platform provides them.
    -   A Spark module that the platform doesn't ship (an external module such
        as `spark-sql-kafka-0-10`) is bundled or passed with
        `spark.jars.packages`, at the target's exact Spark version and Scala
        suffix.
    -   If the target's compiler reports a class that moved out of the JDK or
        the Scala standard library into a separate artifact, add that artifact,
        with `provided` scope if the target's Spark already ships it (see the
        manifest below).
-   **Don't pin GCP connectors.** Remove the Cloud Storage and BigQuery
    connectors (`com.google.cloud.bigdataoss:gcs-connector`, and
    `com.google.cloud.spark:spark-bigquery*` or `spark-<x.y>-bigquery`
    artifacts) from the bundled dependencies, and rely on the platform's
    ("Connectors" in `spark_migration_reference.md`). If the code uses a
    connector's API directly, compile against the target's preinstalled version
    with `provided` scope. Never bundle a second copy of a preinstalled
    connector, relocated or not: change its version only through the platform,
    as that section describes.
-   **Find collisions with the libraries the platform ships.** A library that
    the job bundles and that the target's Spark or Hadoop also puts on the
    classpath, at another version, can collide with it. The libraries of the
    target's Spark are listed in the Apache Spark repository at its release tag,
    in `dev/deps/spark-deps-hadoop-3-hive-2.3` (`spark-deps-hadoop-3.2-hive-2.3`
    before Spark 3.3):

    ```bash
    curl -fsSL https://raw.githubusercontent.com/apache/spark/v<TARGET_SPARK>/dev/deps/spark-deps-hadoop-3-hive-2.3 -o spark_deps_<app_id>_temp.txt
    ```

    Each line is `<artifact>/<version>/<classifier>/<jar>`. The list describes
    Apache Spark's default Scala build, so compare artifact names without their
    Scala suffix. Managed Spark's build can differ slightly, and on clusters
    Hadoop's libraries are on the classpath too: if a cluster of the target
    version is at hand, its `/usr/lib/spark/jars/` directory and
    `hadoop classpath --glob` output are authoritative.

    Compare the list with the dependency tree (section 3), starting with the
    usual collisions: Jackson (`jackson-module-scala` must match the platform's
    `jackson-databind`, or the job fails at startup), Guava, Protobuf, gRPC,
    Netty, Avro, Parquet, Apache Commons, and json4s. Google Cloud client
    libraries bring their own Guava, gRPC, and Protobuf: shade them. For each
    collision, align the job's version with the platform's if the job works with
    it, exclude the library so that the job uses the platform's copy, or shade
    it (next item). Libraries that the job uses from Spark's classpath without
    declaring them change with the target's Spark too; the build checks catch
    their API changes.
-   **Resolve transitive collisions by shading (relocation).** Relocate the
    colliding packages inside the job's jar, so that its copy can't clash with
    the platform's: `maven-shade-plugin` relocations, `sbt-assembly` shade rules
    (`ShadeRule.rename(...).inAll`), or the Gradle Shadow plugin's `relocate`.
    Managed Spark's dependency guide has Maven and sbt examples
    (https://docs.cloud.google.com/managed-spark/docs/guides/manage-spark-dependencies).
    Relocate only libraries that the job bundles, never the `provided` ones or a
    connector.

    -   Exclude signature files (`META-INF/*.SF`, `*.DSA`, `*.RSA`), which
        otherwise fail with `SecurityException: Invalid signature file digest`.
    -   Merge `META-INF/services` files (Maven `ServicesResourceTransformer`, or
        an sbt-assembly merge strategy) so that service providers still load.
    -   Relocation also rewrites string constants that match a pattern, but not
        class names built at run time or written in other resource and
        configuration files: check those for relocated names.
-   **Prioritize the job's classes only as a fallback.** If a colliding library
    can't easily be shaded (for example, because it loads its classes by name
    from configuration files, or its native code is bound to its package names),
    set `spark.driver.userClassPathFirst=true` and
    `spark.executor.userClassPathFirst=true` so that Spark loads the job's jars
    before the platform's classpath.

    -   Both are experimental, and both can break Spark's own classes if the
        job's jars bundle libraries that Spark depends on.
    -   The driver setting applies only in cluster deploy mode
        (`spark.submit.deployMode=cluster`); cluster jobs run their driver in
        client mode by default.
    -   Neither helps when the job passes the library's objects to a platform
        API that expects the platform's version: align the version instead.
    -   Verify the job in Step 2, and record the flags like legacy flags
        (SKILL.md rule 2).
-   **Spark internals.** Code that uses Spark internals has no compatibility
    guarantee, and the migration notes rarely mention their changes: classes
    that the job places in `org.apache.spark` packages to reach `private[spark]`
    or `private[sql]` members, and uses of internal packages such as
    `org.apache.spark.sql.catalyst`, `org.apache.spark.sql.execution`, and
    `org.apache.spark.sql.internal`. Check each such use against the target's
    Spark source at its release tag: the build checks catch removed members, but
    not changed behavior.

## 5. Build Checks Against the Target Version

Build checks show whether the code and its dependencies compile, resolve, and
package against the target versions. Run them twice in Step 1: on the original
code during the analysis (each failure is a finding), and on the changed code
after the upgrade (all checks must pass). Take `<TARGET_SPARK>`,
`<TARGET_SCALA>`, and `<TARGET_JAVA>` from the target's component page.

-   Copy the source tree and its build definition to `build_<app_id>_temp/` and
    run the checks there, so that build output (`target/`, `project/target/`,
    `build/`) never lands in the user's source directories. After recording the
    results, copy out the jar that L3 builds from the changed code—outside any
    Git working copy—under its clean release name (`<jar_name>.jar`) for Step 3
    delivery (and stage it to GCS as `<jar_name>_<app_id>_temp.jar` only for
    Step 2 verification, per section 6), then delete `build_<app_id>_temp/`.
-   For the baseline run on the original code, point the copy's build definition
    at the target (section 3, step 1: `<TARGET_SPARK>`, `<TARGET_SCALA>`, and
    the Java release `<TARGET_JAVA>`), and change nothing else. Maven builds
    that take these versions from properties accept overrides on the command
    line (e.g. `-Dspark.version=<TARGET_SPARK>`; the property names vary by
    project).
-   Use the project's own build tool: its wrapper (`./mvnw`, `./gradlew`) if it
    has one, otherwise the installed `sbt`, `mvn`, or `gradle`.
-   Pick the JDK through `JAVA_HOME`, preferably one of exactly `<TARGET_JAVA>`.
    L1–L3 need a JDK of `<TARGET_JAVA>` or newer (an older one can't compile for
    the target's Java or read the target Spark's bytecode), and L4 needs one
    that the target's Spark supports (`fetch_migration_notes.py` prints them).
    The build tool and its plugins must support that JDK: Gradle lists the Java
    versions that each of its releases supports
    (https://docs.gradle.org/current/userguide/compatibility.html), a plugin
    that is too old fails with errors such as
    `Unsupported class file major version <N>`, and `scala_analysis.md`
    (section 3) covers the Scala compiler and sbt. Record the JDK used in the
    report.
-   If a check can't run (no suitable JDK or build tool, no network access to
    the artifact repositories, or no credentials for a private repository),
    don't install toolchains to force it: record it as "not run" with the
    reason.

### 5.1. L1: Compile (always, when the source and a build tool are available)

```bash
sbt --batch clean compile                 # sbt
./mvnw -B -DskipTests -Dmaven.compiler.showWarnings=true -Dmaven.compiler.showDeprecation=true clean compile    # Maven (or mvn)
./gradlew --no-daemon clean classes       # Gradle (or gradle)
```

-   Each compile error is a finding. In the copy, turn on the compiler warnings
    that the language references list: uses of APIs that the target deprecates
    are findings too (SKILL.md rule 2). If the build turns warnings into errors
    (`-Xfatal-warnings` or `-Werror`), new deprecations fail L1: report them as
    deprecation findings, not as blockers.
-   `class file has wrong version <N>` means that the JDK, or the Java release
    that the build compiles for, is older than the bytecode of the target's
    Spark or of a dependency.

### 5.2. L2: Dependency Resolution (when the build declares dependencies)

```bash
sbt --batch update evicted "show Compile/dependencyClasspath" "show Runtime/fullClasspath"
./mvnw -B dependency:tree
./gradlew --no-daemon dependencies --configuration runtimeClasspath
```

-   Every Scala artifact resolves with the target's suffix, and none with
    another (`_2.12` next to `_2.13`). An artifact that doesn't exist for the
    target's suffix means that the library has no release for the target
    (`scala_analysis.md`, section 1).
-   Spark modules, `scala-library`, Hadoop, and the connectors that the platform
    provides resolve at the target's versions and aren't bundled (section 3,
    step 2).
-   Libraries that the platform also ships are aligned, excluded, or shaded
    (section 4).
-   Jars and packages that the job gets outside the build (`jarFileUris`,
    `spark.jars`, `spark.jars.packages`, and on clusters the `spark:spark.jars`
    and `spark:spark.jars.packages` properties) follow the same rules: the
    target's Scala suffix and Spark version, no connector pins, and no
    collisions.

### 5.3. L3: Package and Inspect the Jar

Build the jar that the job deploys (`sbt --batch assembly` or `package`,
`./mvnw -B -q -DskipTests package`, or `./gradlew --no-daemon shadowJar` or
`jar`), and check that it doesn't bundle what the platform provides (section 4):

```bash
jar tf <JAR> | grep -E '^(scala|org/apache/spark|org/apache/hadoop)/' | head
```

-   A shading or assembly plugin that fails with
    `Unsupported class file major version <N>` is too old for a dependency's
    bytecode: upgrade the plugin. If `sbt-assembly` stops on a `deduplicate`
    error for `module-info.class`, add a merge strategy that discards it.
-   When the Java version changes, list the jar's uses of JDK APIs that the
    target deprecates for removal, and of JDK internal APIs (section 2; `jdeps`
    suggests replacements):

    ```bash
    jdeprscan --release <TARGET_JAVA> --for-removal <JAR>
    jdeps --jdk-internals --multi-release <TARGET_JAVA> <JAR>
    ```

### 5.4. L4: Unit Tests (only if the project has tests that run Spark locally)

Run the project's tests (`sbt --batch test`, `./mvnw -B test`, or
`./gradlew --no-daemon test`) if they run Spark in local mode without external
services: they exercise behavior changes that compiling can't catch, such as
those in the Spark migration notes. Each failure that the version change causes
is a finding. Skip tests that need external services, and say so in the report.

## 6. Verification and Handover

-   **Verification jar (Step 2):** run the jar that L3 built from the changed
    code, named `<jar_name>_<app_id>_temp.jar` (SKILL.md rule 6) and staged as
    "Staged code" in V1 of the verification reference describes. If the job's
    output paths can't be redirected through its arguments or properties (rule
    4), build that jar from a temporary copy of the source with redirected
    paths; the working copy keeps its production paths.
-   **Delivery (Step 3):** the final code is the changed source tree and build
    definition, in their original layout, plus the jar built from them if the
    build checks passed. In the report, name the Java and Scala versions that
    the jar targets; the jar URIs and `spark.jars.packages` coordinates that the
    production job must switch to; and the system hooks removed, connector pins
    removed or overridden, and classpath flags added (sections 3 and 4).
