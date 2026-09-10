# Changelog

## [0.10.1](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.10.0...0.10.1) (2026-09-04)


### Features

* add Bigtable basics skill and EvalBench test cases to DAK ([e06c822](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/e06c822566e46f0d3ccebc969550dd75cc24f944))
* Add resolving-mcp-region-configs skill to Data Agent Common ([0878ed8](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/0878ed83ce665501651c0fd1e5283b135c3e4dd2))
* Add Spark 4.0 BigQuery connector coordinates to gcp-spark skill ([e86233d](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/e86233ddaeee10a10ffcdc564bc792a46cd85944))
* **mcp:** route Google Cloud MCP services through bundled Node stdio proxy ([d17797d](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/d17797deff4205936ad1a578934178b82e55928d))
* Simplify claude user config by removing BigQuery location and ProjectId string. ([44d991f](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/44d991fa9ced624181fd7a8b1ed3e26cadb47dfa))
* **skills:** Update managing_python_dependencies with pre-flight environment check bundling ([ad94694](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/ad94694cb96cbda89fa45e5b18b47cd722bd6645))


### Bug Fixes

* Update BigFrames skills to reduce agent confusions. ([deabd80](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/deabd800d918d877be7dc47127f5bc2436a8e6e2))


### Miscellaneous Chores

* force release 0.10.1 ([#309](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/309)) ([6c33297](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/6c3329771bdb2f118ba288cbba6c4cdb7d105b13))

## [0.10.0](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.8.0...0.10.0) (2026-08-31)


### Features

* Add semantic schema mapping skill for ontology driven data engineering ([f015039](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/f01503992d4308bcc90792b7aa2ae35a1653f3ee))
* Add Spark Connect session lifecycle guide with DataprocSparkSession to gcp_spark skill ([b977284](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/b97728471647bc2eaf38ce49022c8414caa5de5a))
* Avoid redundant cluster creation for serverless batch jobs in gcp_spark skill ([15d9e27](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/15d9e272522613e49a6b0853b5d677ae4d287376))
* Enforce argparse parameterization for Spark scripts in gcp_spark skill ([d0cf7eb](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/d0cf7eb914a204a74f8406ad51597101f7764a23))
* Enforce Python standard logging over print() in gcp_spark skill ([29f17a0](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/29f17a0843cd1858b96a989ffb4ff2fd7f898b29))
* **orchestration:** update orchestration pipeline schema ([eb5f3e3](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/eb5f3e389d8ab56510ea7bf496da96edd02438bd))
* **orchestration:** update orchestration pipelines schema to support AI actions ([fc13f54](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/fc13f5430aa6a24924b746b76409fa3393aaea74))
* Remove hardcoded secrets from Cloud SQL examples in gcp_spark skill ([682aee5](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/682aee5a0e49072a30625ec685820e1a50ec7cda))
* **skills:** Update google-cloud-auth-verification with bundled probe and IAM handling ([a891ebc](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/a891ebc5aec2812355977ef85e046bd95dc5e472))
* Use @toolbox-sdk/server@latest and remove Windows-specific quoting ([4e51d1c](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/4e51d1c03cb56e5ca09c90b2fbae6df5dd9dea91))


### Bug Fixes

* Preserve host attribution values when tagging gcloud commands. ([e830e87](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/e830e879a1278367e5e45eace4da12b10fcb290c))
* **skills:** Generalize GCP auth verification pre-flight hierarchy ([fd3ac55](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/fd3ac5583d387b037e1862c042c70635dec6074c))
* **skills:** Remove unsupported aliases field from google-cloud-auth-verification frontmatter ([3bc2e21](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/3bc2e21d6f847ee6e537a7d44acf2ae7cf24349b))


### Miscellaneous Chores

* force release 0.10.0 ([3dd3f00](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/3dd3f00f21ba5209ebd9039dbdbb6c80783b0ccf))

## [0.8.0](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.7.2...0.8.0) (2026-08-07)


### Features

* **plugin:** support agent plugin spec ([a9b14ea](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/a9b14ea88087f59b3d65ce653c9a39a81efaff01)), refs [#198](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/198)


### Miscellaneous Chores

* force release 0.8.0 ([35a2768](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/35a2768d96d7bca6073ec067de92cf066c005ff3))

## [0.7.2](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.7.1...0.7.2) (2026-07-28)


### Features

* **skills:** Clarify BQ label enforcement rules for resource attribution. ([c16b546](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/c16b5465d6dba54f089e8ed8ac83d38ed5cc4aae))
* **skills:** Update bq label flag syntax in resource attribution skills. ([1ff44be](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/1ff44bec65a1a7913e772892c9a2542006c584b2))


### Miscellaneous Chores

* force release 0.7.2 ([62d2f9c](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/62d2f9c5504297893251a32ca92ec34c5ae2eb67))

## [0.7.1](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.7.0...0.7.1) (2026-07-27)


### Bug Fixes

* remove default hooks ([1171475](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/1171475ffa60507cf06eaa5d9a1b459db467b670))

## [0.7.0](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.6.1...0.7.0) (2026-07-24)


### Features

* Add AI.AGG function to Data Agent Kit ([9431ff2](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/9431ff2d66468dcbe578499367699eba6cf03af3))
* Bigtable MCP support ([26f175e](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/26f175e8e3f29a5e4103a05a102a522a5dcd7861)), refs [#146](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/146)
* Bigtable MCP support ([c58f5e9](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/c58f5e9d98d9cf94052d049712af8d27e03be5c8)), refs [#146](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/146)
* Modularize BigQuery skills in data_agent_common ([b29c63a](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/b29c63acb4e3d7f44b51bc8cb68785bb4d2a170f))
* Remove DB skills, which are just wrappers on MCP toolbox from data agent common. Will add helpful skills once we come up with them. ([a9beba2](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/a9beba24337cd4d9994ece7faab4adadd7e19bdb))
* **skills:** Add more IDE/environment values for resource attribution environment labels. ([3941694](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/3941694cf37f326e81a74eeee514c2163d67c7f6))
* Update BQ ai_function_best_practices and constraints. ([f4394e1](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/f4394e1e9de1d877af3238e9d332f0f259aa7bb9))


### Bug Fixes

* Fix telemetry hook configurations for Codex, Claude Code, and Gemini CLI. ([b93ca2e](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/b93ca2ea387872d2b7378b0e56671cedf3d32517))
* Update skill references and bump version in dataform and dbt. ([879f134](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/879f13499d5566ce2146050c2a8bce44abd69526))


### Miscellaneous Chores

* force release 0.7.0 ([3e89ba0](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/3e89ba0527440893bcd085aa69fd1943c9e2c576))

## [0.6.1](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.4.0...0.6.1) (2026-07-10)


### Features

* Duplicate graph-schema component to bigquery skill ([b5bc330](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/b5bc330f03758618e63cecd8e47c5f1ac87af2c1))
* gcp-managed-airflow-migration - a new skill for Airflow code migration ([de2d876](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/de2d876d6d3a8f555df2f833b3a2db5ef07d194e))
* rename plugin to dak and remove toolbox from mcp server names ([#99](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/99)) ([cb3a6e8](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/cb3a6e85b7b0607c09479216597a92f0dcf693ce))
* **skills:** Add AlloyDB Omni skills ([94b8582](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/94b858250a5e099daa0ea9803077d0129d06cf14))
* **skills:** Add AlloyDB skills ([fb5bd8b](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/fb5bd8b96bbdc5507a32df236efa50df9b5ef638))
* **skills:** Add Cloud SQL MySQL skills ([7f2442a](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/7f2442abee545a2b75cdb3052be2482fb316cdbc))
* **skills:** Add Cloud SQL Postgres skills ([420e3ac](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/420e3ac34deab005668e43a3507db160b760fb05))
* **skills:** Add Cloud SQL SQL Server skills ([7e887d0](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/7e887d0836ab4d5e1bfc46307115b43ee2d9d7ec))
* **skills:** Add Firestore Native skills ([f6fa0df](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/f6fa0df968b45f4760185135e88e26b76f9c35ca))
* **skills:** add github-release-skill and update Copybara reviewers ([ca05037](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/ca050377cda6083ffa2be59785fb099150d6428e))
* **skills:** Add Spanner skills ([c1dc599](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/c1dc5990d698da3a9f82af390632d36b1880a2a7))
* Update DAK Skill to support Gemini CLI, Claude Code, and Codex attribution tags ([e1922d8](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/e1922d8efb1770ed54d7a9758d3a5f7863b1f5a6))


### Bug Fixes

* restore repository dotfiles and workflows deleted by sync ([#114](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/114)) ([beea04b](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/beea04b27a778c95f92134f8140bf5c8b6eb8ab8))


### Miscellaneous Chores

* force release 0.6.1 ([e259079](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/e259079e4f5a472d1c162063148da00fdf9b7599))
* force release 0.6.1 ([dbc59f7](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/dbc59f7892b94e3672a526d3eb9d5c865c218a85))

## [0.4.0](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.2.0...0.4.0) (2026-06-11)


### Miscellaneous Chores

* force release 0.4.0 ([#93](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/93)) ([23aab90](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/23aab90cf7a198e8481dce1475020e14014a7ebe))

## [0.2.0](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.1.4...0.2.0) (2026-05-15)


### Features

* update skills from cloudtop ([#70](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/70)) ([f094668](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/f0946689ea9b5bd1f1a56225b24d5f5f4da95f87))


### Miscellaneous Chores

* force release 0.2.0 ([#72](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/72)) ([90311ce](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/90311cea40d6ebac8189fcced17e5b98d384e681))

## [0.1.4](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.1.3...0.1.4) (2026-05-07)


### Features

* prompt and configure GCP and BigQuery variables during installation ([#54](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/54)) ([e12d327](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/e12d3279b5bd97e88522427510d18dd7a43c1626))

## [0.1.3](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.1.2...0.1.3) (2026-05-06)


### Bug Fixes

* Update codex commands version ([#56](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/56)) ([f78aa61](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/f78aa61e586f01b45581149bd5b9a2c3f9de70fd))

## [0.1.2](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.1.1...0.1.2) (2026-05-04)


### Features

* split notebook and visualization MCP servers ([#51](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/51)) ([3e4c2d1](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/3e4c2d16f06c90c44b9c0df51ae8c91ef452d559))


### Bug Fixes

* use tags for codex installation scripts ([#52](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/52)) ([6cd5114](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/6cd5114531dc807c9b8894b3511bb7b399afabad))

## [0.1.1](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.1.0...0.1.1) (2026-04-28)


### Features

* separate MCP configurations for Claude and Codex ([#49](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/49)) ([33bbdd9](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/33bbdd95b59610ee503e8ee3f63a761f9f214990))

## [0.1.0](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/compare/0.1.8...0.1.0) (2026-04-20)


### Features

* Feature/codex install update ([#35](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/35)) ([ac4d3b2](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/ac4d3b20e35c776ee0c5a5aaffb71b06772b3df5))
* Infer IDE from process tree ([#40](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/40)) ([f3ccd0d](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/f3ccd0dda4e5d97504e2f90b98376096301f9b01))
* Sync data cloud skills ([#38](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/issues/38)) ([b3f3350](https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack/commit/b3f3350f112f29d0652336e8686764953239f5c4))
