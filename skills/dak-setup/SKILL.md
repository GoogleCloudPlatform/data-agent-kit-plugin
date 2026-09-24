---
name: dak-setup
description: Configures (or reconfigures) the Google Cloud Data Agent Kit (DAK) plugin by checking gcloud and ADC credentials, collecting the GCP project ID, region, and services, and running its bundled `dak-setup` script. Use this proactively and without waiting to be asked whenever a SessionStart hook or any other system/context message reports that the Data Agent Kit plugin is not configured, is missing configuration, or needs to be reconfigured. Also use it whenever the user mentions setting up, configuring, reconfiguring, or changing the project, region, or service integrations for the Data Agent Kit or DAK plugin — even if they phrase it casually, like "dak isn't working" or "I want to enable more GCP service integrations".
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# Data Agent Kit setup

Walk the user through configuring the Data Agent Kit plugin, run the setup command, and tell them to restart their agent so the new configuration loads.

This skill is usually triggered by a SessionStart hook rather than by the user, so the user may not be expecting it. Open with one short sentence explaining what's happening and why ("The Data Agent Kit plugin isn't configured yet — let me get that sorted, it'll take a minute"), then start at step 1.

Run the steps in order. Each step depends on the one before it: there's no point asking for a project ID if the user can't authenticate, and no point running setup with a guessed region. If a step can't be completed, stop there, explain what's blocking, and pick up from that step once the user resolves it.

## Step 1 — Verify gcloud is installed

```bash
gcloud --version
```

If the command is found, continue silently — no need to report the version.

If it isn't found, **stop**. Tell the user gcloud is required and point them at the install docs: https://cloud.google.com/sdk/docs/install. Do not try to install it yourself; the right installation method depends on their OS and package manager, and a wrong guess leaves a broken SDK behind. Offer to resume setup once they've installed it and reopened their shell.

## Step 2 — Verify ADC credentials

```bash
gcloud auth application-default print-access-token > /dev/null 2>&1 && echo "ADC_OK" || echo "ADC_MISSING"
```

Redirect the output as shown. The raw command prints a live access token, and tokens should never land in the transcript, in scrollback, or in a log file.

If the result is `ADC_MISSING`, tell the user you're going to open a browser sign-in flow, then run:

```bash
gcloud auth application-default login
```

Notes for this command:

- It's interactive and blocks until the user finishes in the browser. Run it in the foreground with a generous timeout (several minutes), not in the background.
- If the environment is headless (SSH session, container, no display), use `gcloud auth application-default login --no-launch-browser` instead, which prints a URL and waits for a verification code.
- Afterwards, re-run the check from the top of this step to confirm it worked. If it still fails, stop and show the user the actual error rather than retrying.

## Step 3 — Ask for the GCP project ID

First check whether gcloud already has one configured, so the user can just confirm instead of typing it out:

```bash
gcloud config get-value project 2>/dev/null
```

Then ask. If a project was detected, offer it as the default while making clear they can use a different one — use whatever interactive prompt or option picker you have available, or simply ask in chat. Either is fine, but do not proceed on a guess. An unset value prints `(unset)` or nothing; treat that as "no default" and ask outright.

Sanity-check the answer before moving on: a project **ID** is lowercase letters, digits, and hyphens (6–30 characters), not the display name and not the numeric project number. If the user gives something that looks like a display name ("My Data Project"), ask them to confirm the ID — `gcloud projects list` will show both columns if they're unsure.

## Step 4 — Ask for the GCP region

Check for a configured default the same way:

```bash
gcloud config get-value compute/region 2>/dev/null
```

Ask for the region, offering the detected value if there is one and a few common choices otherwise (`us-central1`, `us-west1`, `us-east4`, `europe-west1`, `europe-west3`, `asia-northeast1`, `asia-east1`), plus the option to enter something else. Show choices that are in geographically proximity to the user.

Expect a region like `us-central1`, not a zone like `us-central1-a`. If the user gives a zone, point out the difference and confirm the region with them rather than silently trimming the suffix.

## Step 5 — Ask which service integrations to enable

Present this exact list of services, numbered, and ask the user to pick one or more services that Data Agent Kit should enable integration for:

1. BigQuery
2. Knowledge Catalog
3. AlloyDB
4. Cloud SQL
5. Spanner
6. Bigtable
7. Firestore
8. Cloud Storage
9. Apache Spark
10. Apache Airflow
11. Dataflow

Let them answer however is natural — numbers, names, or "all". Ask this as a plain numbered list in chat rather than through an option picker: the list is long enough that most pickers would force it into awkward groups, and multiple selections are easier to express in a single reply.

Two things matter when interpreting the answer:

- **At least one service is required.** If the user picks none, ask again.
- **Use the exact strings above** in the setup command, including capitalization and internal spaces (`Knowledge Catalog`, not `knowledge-catalog` or `KnowledgeCatalog`). Map whatever the user typed back onto these canonical names. Each selected service is passed to the script as its own quoted argument — see step 6.

## Step 6 — Run the setup command

The setup script ships with this skill at `scripts/dak-setup.js`, directly alongside this SKILL.md. Resolve that path against the directory this file was loaded from, not against the shell's working directory — the shell almost always starts in the user's project, not in the skill directory, so a bare `scripts/dak-setup.js` will not be found. Either pass the full path to `node` or `cd` into the skill directory first.

Show the user a one-line summary of what you collected (project, region, services), get a quick confirmation, then run:

```bash
node "<skill directory>/scripts/dak-setup.js" save --project-id "<project id>" --region "<region>" --services "<service1>" "<service2>" "<service3>"
```

Details that matter:

- `save` is a subcommand and comes immediately after the script path, before any flags.
- Flag values are separated by a **space**, not an `=` sign (`--project-id "acme-prod"`, not `--project-id="acme-prod"`).
- Flags use **two ASCII hyphens** (`--project-id`). If you're copying the command from anywhere, check that an en dash (`–`) hasn't crept in — it looks nearly identical and the command will fail to parse.
- `--services` takes a **variadic list**: each service is its own separately quoted argument, space-separated, with the flag written only once. Quoting each one individually is what keeps names like `Knowledge Catalog` from being read as two services. Do not join them with commas.
- Pass exactly as many service arguments as the user selected — one is fine, and there's no fixed count.
- Quote the script path too. Plugin install directories can contain spaces, and an unquoted path splits into two arguments.
- Example: `node "/home/ana/.claude/plugins/data-agent-kit/skills/setup/scripts/dak-setup.js" save --project-id "acme-analytics-prod" --region "us-central1" --services "BigQuery" "Cloud Storage" "Dataflow"`
- Setup can take a few minutes depending on how many services were selected. Run it in the foreground with an extended timeout (around 10 minutes) so it isn't killed partway through.
- If the script isn't at that path, stop and tell the user the plugin looks incompletely installed. Do not fall back to `npx dak-setup`: the package isn't published, so npx fails with a registry error that reads like a network problem and sends the user down the wrong path entirely.

When it succeeds, tell the user the plugin is configured, summarize what was enabled, and then deliver the restart notice below. When it fails, show the relevant error output and diagnose it rather than re-running the same command — common causes are a project ID typo, an unsupported region, or the ADC account lacking permission on the project.

## Step 7 — Tell the user to restart, and don't use the plugin until they do

The configuration is only picked up when the plugin loads, which happens at session start. Nothing written by `dak-setup` takes effect in the session that's currently running.

Tell the user plainly, as the last thing you say:

> The Data Agent Kit is configured. Restart your agent for the changes to take effect — the plugin's tools won't be available until this session ends and a new one starts.

This applies to you as well, not just to the user. For the remainder of this session:

- Do not try to call Data Agent Kit tools or commands, and do not claim the plugin is ready to use right now. Its tools aren't loaded, so any attempt will fail in a confusing way and make it look like setup didn't work.
- If the user asks you to do something with the plugin before restarting, remind them a restart is needed rather than attempting it and reporting an error.
- If the SessionStart hook fires again after the restart and still reports the plugin as unconfigured, that's a real failure — go back through this skill and check the values that were passed, rather than assuming the restart just hasn't happened yet.

You can keep helping with anything unrelated in the meantime; the user doesn't have to restart immediately, only before using the plugin.

## If this is a reconfiguration

When the hook says the plugin *needs to be reconfigured* rather than that it's unconfigured, the steps are the same, but mention any existing configuration you can see when asking in steps 3–5 so the user only has to change what's actually different. Re-running `dak-setup` overwrites the previous configuration, so confirm the full set of services they want — anything omitted from the new list is dropped, not merged with the old one.

The restart requirement in step 7 applies here too, and is easier to overlook: the plugin is already loaded with the *old* configuration, so it will appear to work while quietly using the previous project, region, or service set. Be explicit that the new settings are inactive until a restart.
