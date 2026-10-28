<!-- disableFinding(LINE_OVER_80) -->

# Knowledge Catalog Constructs in OKF v0.2 (`references/kc_constructs/SUBSKILL.md`)

A Knowledge Catalog **context set** is an entry group (`type: context-set`) whose entries and links
are authored on disk as **Open Knowledge Format (OKF v0.2)** markdown files under `bundle/`.

Read `references/kc_constructs/output_contract.md` alongside this file for exact frontmatter and body
templates.

---

## 1. Bundle directory layout & entry IDs

Let:

- `<CS_ID>` = context set entry group ID (e.g., `retail-orders-context`)
- `<PROJECT>` = GCP project hosting the context set (e.g., `my-gcp-project`)
- `<LOCATION>` = entry group location. If the user doesn't name one, use the location of the
  BigQuery datasets the context set covers (e.g., `us` for `US` multi-region datasets), not `global`;
  if the datasets span locations, ask.

Inside `bundle/`, `kcmd` namespaces files under `<CS_ID>/<PROJECT>/<LOCATION>/` (or you may place
files under that namespace directory; `kcmd` maps `<CS_ID>/<PROJECT>/<LOCATION>/<entry-id>.md` to
entry ID `<entry-id>`).

### Progressive Disclosure Hierarchy (mandatory for full context sets)

Consumption agents (like Gemini Data Agent / Concord) traverse a context set top-down starting at
`agents`:

```
bundle/<CS_ID>/<PROJECT>/<LOCATION>/
├── agents.md                                               # entry ID: agents (Root router)
├── assets.md                                               # entry ID: assets (parent: agents)
├── assets/
│   └── bigquery/
│       ├── <bq_project>.md                                 # entry ID: assets/bigquery/<bq_project> (parent: assets)
│       └── <bq_project>/
│           ├── <dataset>.md                                # entry ID: assets/bigquery/<bq_project>/<dataset> (parent: assets/bigquery/<bq_project>)
│           └── <dataset>/
│               └── <table>.md                              # entry ID: assets/bigquery/<bq_project>/<dataset>/<table> (parent: assets/bigquery/<bq_project>/<dataset>)
├── documents.md                                            # entry ID: documents (parent: agents)
├── documents/
│   └── <slug>.md (or concepts/<slug>.md)                   # entry ID: documents/<slug> or documents/concepts/<slug> (parent: documents or documents/concepts)
└── query-templates/
    └── <slug>.md                                           # entry ID: query-templates/<slug> (flat, no parent)
```

> **Important ID rules:**
> - File names `index.md`, `log.md`, and `*.ref.md` are **reserved by OKF** and are NOT parsed as
>   KC concept entries (`index.md` files are auto-generated directory listings created by `kcmd`).
> - Therefore, the root router entry is `agents.md` (`agents`), the top-level category indexes are
>   `assets.md` (`assets`) and `documents.md` (`documents`), and a concept folder index is a
>   **sibling** file (`documents/concepts.md` for folder `documents/concepts/`, NOT
>   `documents/concepts/index.md`).

---

## 2. How the 4 KC construct types map to OKF v0.2 files

| Construct | Entry ID pattern | OKF Frontmatter `type:` | Required Frontmatter & Body |
| :--- | :--- | :--- | :--- |
| **1. Progressive-Disclosure Index** (`agents`, `assets`, `documents`, `assets/bigquery/<p>`, `assets/bigquery/<p>/<d>`) | `agents`, `assets`, `documents`, `assets/bigquery/<p>/<d>` | `type: Knowledge Base Index` | `title`, `description`, `parent` (except on `agents` and top-level `query-templates`), plus a Markdown **Contents** table linking to every child entry (`[Title](/<CS_ID>/<PROJECT>/<LOCATION>/<child-id>.md)`). |
| **2. Table Context Document** | `assets/bigquery/<bq_project>/<dataset>/<table>` | `type: Table Context` | `title`, `description`, `parent: assets/bigquery/<bq_project>/<dataset>`, `resource: projects/<PROJECT>/locations/<BQ_LOC>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<DATASET>/tables/<TABLE>`. Body: Table Grain/Purpose, Key Columns table, Join Keys, Filtering Rules & Caveats. |
| **3. Knowledge Base Document** (business concepts, metrics, SOPs, policies) | `documents/<slug>` or `documents/concepts/<slug>` | `type: Knowledge Base` | `title`, `description`, `parent: documents` (or `documents/concepts` if `documents/concepts.md` exists). Body: authoritative definition, formula/SQL rule, edge cases, source citations, and `> **Open question:**` if sources conflict. |
| **4. Query Template** (verified golden SQL) | `query-templates/<slug>` | `type: Query Template` | `title` (the natural-language question, `nlQuery`), `description` (the analytical `intent` — must explain *how/why* and NOT be a copy of `title`), `sourceType: BIGQUERY`, `parameters:` list (`name`, `type`, `description`, `sampleValues`), and a fenced ```` ```sql ```` block in the body. No `parent`. |

---

## 3. Cross-references and Entry Links

There are two complementary ways entries connect in a context set:

### A. Markdown links inside overview bodies (SPEC §6.1)

Inside any `.md` body:

- In a **Contents table cell** (in `agents.md`, `assets.md`, `documents.md`, etc.), link to a child
  entry using its bundle-root path:
  ```markdown
  | [Orders Table](/<CS_ID>/<PROJECT>/<LOCATION>/assets/bigquery/<bq_project>/<dataset>/orders.md) | Order header grain and status rules |
  ```
  *(When `kcmd` parses this table cell, it automatically converts the link to `catalog/<entry-id>`
  for KC consumption!)*
- In **prose**, link to another entry in the bundle with `[Label](/<CS_ID>/<PROJECT>/<LOCATION>/<entry-id>.md)`
  or backtick `` `<entry-id>` ``.

### B. Entry Links in `bundle/_links.yaml` (or frontmatter `extra.links`)

Author rich semantic links in `bundle/_links.yaml` at the root of `bundle/`:

1. **`definition` (directed, `SOURCE` → `TARGET`):** Only for linking an entry in this context set
   to an **existing `@dataplex` Business Glossary term**: `source` is the context-set entry (a
   `documents/...`, table-context, or query-template page) and `target` is the glossary term's full
   resource name. Never point a `definition` link at another page in the context set (Knowledge
   Catalog rejects a document as a `definition` target at push time).
2. **`related` (undirected):** Connects a `Query Template` to the `Table Context` and
   `Knowledge Base` entries it uses, a concept doc to the table-context or template pages it governs,
   or two `Table Context` entries that are commonly joined.
   **Every `Table Context` entry also gets a `related` link to its `@bigquery` source entry** (the
   same full resource name as its `resource:` frontmatter).

> **No `schema-join` links.** Writing `schema-join` links between source tables is out of scope for
> context sets. Record join keys and cardinality as text in each `Table Context` doc's
> **Join Relationships** section, and connect the two tables with a `related` link.
