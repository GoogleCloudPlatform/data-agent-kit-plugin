# Phase 3: Output Based on User Intent

This phase handles generating the final bucket configuration in the user's
preferred format and executing the creation if authorized.

## Step 1: Determine Preferred Format

The agent must determine the user's preferred output format.

*   If the user has already specified a format in their prompt (e.g., "give me
    Terraform", "write a gcloud command"), use that format.
*   If the format is not specified, the agent MUST ask the user to select one of
    the following formats:
    *   **gcloud**: Command-line interface commands.
    *   **REST (JSON)**: JSON payload and corresponding `curl` command.
    *   **Terraform**: Terraform configuration block.
    *   **SDK**: Client library code snippet. If selected, ask for the preferred
        language (C++, Java, Python, or Go).

--------------------------------------------------------------------------------

## Step 2: Generate Configuration Snippet and Recommendations

1.  Based on the confirmed **Draft Bucket Creation Plan** (from Phase 2) and the
    selected format, generate the configuration using the templates and rules in
    the corresponding reference file:

    *   **gcloud**: Refer to [gcloud.md](gcloud.md)
    *   **REST (JSON)**: Refer to [rest.md](rest.md)
    *   **Terraform**: Refer to [terraform.md](terraform.md)
    *   **SDK**: Refer to [sdk.md](sdk.md)

2.  **CRITICAL**: Ensure that all generated commands, payloads, configurations,
    or code snippets—including any auxiliary or prerequisite commands/requests
    in the **Other Recommendations** section—include the appropriate attribution
    tagging as described in `SKILL.md` and the respective reference files.

3.  **CRITICAL**: In your final output, you MUST include a section for **Other
    Recommendations** (such as Cloud Monitoring, Storage Insights, or
    prerequisite IAM bindings) that were proposed in the draft plan. Describe
    their purpose and provide the necessary commands or guidance for the user to
    configure them.

4.  **CRITICAL**: If the reference files indicate version support limitations
    for any of the configured features (e.g., Encryption Enforcement Config in
    SDKs), you MUST include a warning in the final output. The warning must
    specify the minimum supported version and instruct the user to use
    alternative methods (REST, gcloud, or Terraform) if they are using an
    unsupported version.

Present the generated command/code block and recommendations to the user.

--------------------------------------------------------------------------------

## Step 3: Execution and Delivery

The action to take depends on the selected format:

### For `gcloud` and `REST` (JSON)

1.  Display the full command (including the payload for REST).
2.  Explicitly ask the user for confirmation to execute the command: > "Would
    you like me to execute this command to create the bucket now? Please
    confirm."
3.  **CRITICAL**: Do NOT execute any command without explicit, affirmative
    confirmation from the user.
4.  If confirmed:
    *   Execute the command.
    *   If successful, report success and provide the bucket details.
    *   If it fails (e.g. permission error, network issue), report the error
        details to the user and suggest they run the displayed command manually.

### For `Terraform` and `SDK`

1.  Display the configuration snippet or code block.
2.  Do NOT offer to execute or apply it, unless the user has explicitly
    requested to update a specific file in their workspace.
3.  Instruct the user on how to integrate the snippet into their project.
