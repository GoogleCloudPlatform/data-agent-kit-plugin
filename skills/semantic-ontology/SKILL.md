---
name: semantic-ontology
license: Apache-2.0
metadata:
  version: v1
  publisher: google
description: >-
  Locates and fetches a governed Open Semantic Interchange Google Flavor (OSI+G) semantic model for the data in scope: local workspace YAML first, then Knowledge Catalog, then Context Sets or BigQuery property graphs as fallbacks.
  Use whenever a task needs a semantic model / ontology or the entities, relationships, metrics, and field-level rules it defines (schema mapping, dbt/ELT pipeline generation, semantic modeling) — even if the BigQuery project, dataset, or table ID is already provided.
  Do NOT use for generic table/dataset discovery or for authoring/publishing models with kcmd.
---

# Semantic Ontology (`OSI+G`)

Locate a governed `OSI+G` semantic model (`version:` typically matching `0.2.*`,
e.g., `"0.2.0.dev0/google"` or Ossie `"0.2.0.dev0"`) and read it back
completely. The model is self-describing: this skill only covers where to find
it and how to fetch it.

## Step 0: Verify Environment

Confirm the workspace root and, if querying remote catalogs, verify the target
`<PROJECT_ID>` and whether `knowledge_catalog` MCP tools or `gcloud` / `bq`
credentials are available.

## Resolution Order

Stop at the first tier that yields a model for the tables in scope.

1.  **Local workspace YAML (check first)**

    -   Look for `*.yaml` / `*.yml` files whose root keys are `version:` and
        `semantic_model:` — typically a `kcmd` workspace
        `catalog/EntryGroups/<entry_group>/<model>.yaml`, or a path the user
        mentions. Quick scan:
        `find . -maxdepth 5 \( -name "*.yaml" -o -name "*.yml" \)` (or `python3
        -c "import pathlib; [print(p) for p in pathlib.Path('.').rglob('*') if
        p.suffix in ('.yaml', '.yml')]"`).
    -   If found, read it directly. It may carry unpushed edits, so it is
        authoritative; cite the file path as the source. You may still run Tier
        2 Step A to report whether a published copy differs, but do not replace
        the local model with it. If several files match, pick the one whose
        `entities[].source` reference the tables in scope.

2.  **Knowledge Catalog (published models)** — two steps:

    -   **Step A — find the model entry** (search also indexes semantic ontology
        and `guidelines` aspects)

        -   MCP (`knowledge_catalog`):

            ```text
            search_entries(
              project_id="<PROJECT_ID>",
              query="type=projects/dataplex-types/locations/global/entryTypes/semantic-model")
            ```
        -   CLI:

            ```bash
            gcloud dataplex entries search "type=projects/dataplex-types/locations/global/entryTypes/semantic-model" \
              --project="<PROJECT_ID>" --limit=20 --format="value(name)"
            ```
        -   From the returned `name`
            (`projects/<N>/locations/<LOC>/entryGroups/<EG>/entries/<MODEL_ID>`)
            note `<LOC>`, `<EG>`, `<MODEL_ID>`.
    -   **Step B — expand the model (`lookup_context` primary, `.files.`
        fallback)**

        -   **Primary — `lookup_context` on the `semantic-model` entry** to
            expand child `Semantic Entity`, `Semantic Metric`, and
            `Semantic Relationship` entries (`relatedResources`),
            `semantic-link` edges, and `guidelines` in one call:

            -   MCP (`knowledge_catalog`):

                ```text
                lookup_context(
                  project_id="<PROJECT_ID>", location="<LOC>",
                  resources=["projects/<N>/locations/<LOC>/entryGroups/<EG>/entries/<MODEL_ID>"])
                ```
            -   CLI:

                ```bash
                gcloud dataplex context lookup \
                  --project="<PROJECT_ID>" --location="<LOC>" \
                  --resources="projects/<N>/locations/<LOC>/entryGroups/<EG>/entries/<MODEL_ID>"
                ```
        -   **Fallback — read `<MODEL_ID>.files.<MODEL_ID>.yaml` (`view=ALL`)**
            if `lookup_context` returns only the root model without
            `relatedResources` (or omits YAML-level SQL `expression`s or
            `ai_context.synonyms`/`examples`, stored in aspect
            `*.semantic-model-file` field `data.content`):

            -   MCP (`knowledge_catalog`):

                ```text
                lookup_entry(
                  project_id="<PROJECT_ID>", location="<LOC>", view="ALL",
                  entry="projects/<N>/locations/<LOC>/entryGroups/<EG>/entries/<MODEL_ID>.files.<MODEL_ID>.yaml")
                ```
            -   CLI:

                ```bash
                gcloud dataplex entries describe "<MODEL_ID>.files.<MODEL_ID>.yaml" \
                  --project="<PROJECT_ID>" --location="<LOC>" --entry-group="<EG>" --view=ALL --format=json \
                  | jq -r '.aspects | to_entries[] | select(.key | endswith(".semantic-model-file")) | .value.data.content'
                ```
    -   **Auth in headless containers**: if `gcloud` fails with
        `Reauthentication required` / `Context Aware Access`, use the
        `knowledge_catalog` MCP tools (ADC-backed) or prefix `gcloud` with

        ```bash
        CLOUDSDK_AUTH_ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
        ```
    -   **Context Set entry groups** (older / hand-curated layout): search

        ```text
        labels.type=context-set type=projects/dataplex-types/locations/global/entryTypes/entrygroup
        ```

        (keyword mode: `label.type=context-set`), then list child entries with

        ```text
        name:projects/<N_OR_ID>/locations/<LOC>/entryGroups/<CONTEXT_SET_ID>/entries
        ```

        and `lookup_context` the model / entity / overview entries.
    -   If `kcmd` is on `PATH` and the user wants the files locally:
        `kcmd init --semantic-model <PROJECT_ID>.<LOC>.<EG>` then `kcmd pull`.

3.  **BigQuery property graph (last resort)** — a graph is usually a
    materialization of a model and lacks `ai_context`, filters, and metric
    meaning. Only if no model was found (use `<DATASET_ID>` when known, or
    `region-<REGION>` such as `region-us` for dataset-independent discovery):

    ```bash
    bq query --use_legacy_sql=false \
      "SELECT * FROM \`<PROJECT_ID>.<DATASET_ID>.INFORMATION_SCHEMA.PROPERTY_GRAPHS\`"
    bq query --use_legacy_sql=false \
      "SELECT * FROM \`<PROJECT_ID>.region-<REGION>.INFORMATION_SCHEMA.PROPERTY_GRAPHS\`"
    ```

## After Fetching

-   Report the source: workspace file path, or Knowledge Catalog entry group /
    entry names.
-   Hand the model through as authored — `entities[]` (`source`, `primary_key`,
    `fields[]`), `relationships[]`, `metrics[]`, and all `ai_context` /
    `description` text — for downstream skills to consume; do not paraphrase or
    re-derive it from sample data.
-   If you fell back to structured entries or a property graph, say what is
    missing.
