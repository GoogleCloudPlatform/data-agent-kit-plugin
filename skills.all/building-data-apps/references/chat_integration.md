# Gemini Data Analytics Chat Integration

> [!CAUTION] Ensure data sources exists as BigQuery tables.

> [!WARNING] **Common Error: `400 REFERENCES_NOT_SET`** This happens when
> `datasource_references` is missing from `inline_context`. The API **REQUIRES**
> at least one BigQuery table reference. Do not use BigLake/Iceberg tables, they
> are unsupported.

## Architecture Requirements

You MUST implement the chat using the following state-of-the-art patterns:

1.  **Server-Sent Events (SSE)**: The backend API MUST stream the response
    chunk-by-chunk using a generator (`text/event-stream`). Do not wait for the
    generation to finish fully.
2.  **Thought vs Content Segregation**: The backend must extract
    `chunk.system_message.text_type` (or `chunk.system_message.text.text_type`
    depending on SDK nesting) and emit blocks typed as `"THOUGHT"` instantly,
    completely separate from the `"FINAL_RESPONSE"` text. The backend should
    also pass along `"SUGGESTION"`s (follow-up interactive buttons), which the
    frontend MUST render as clickable follow-up prompts.
3.  **Multi-Turn Support**: The chat interface MUST support multi-turn
    conversations, allowing users to ask follow-up questions. This requires
    maintaining conversation history and context.
4.  **Structured UI Parsing**: The frontend React app loop MUST intercept and
    buffer the SSE stream, maintaining distinct state properties (`m.thoughts`
    vs `m.content`).
5.  **Markdown Formatting**: You MUST use `react-markdown` + `remark-gfm`
    wrapped in a localized `<div>` containing Tailwind Typography overrides
    (`[&>p]:mb-2 [&>h3]:...`) instead of dumping unstructured blobs into the
    chat. Avoid passing `className` strictly to the root `ReactMarkdown`
    component to prevent version 10+ rendering crashes.
6.  **Dynamic UX**: Expose the backend thoughts locally as a dynamically
    iterative title line (e.g. tracking the very last `\n` mapped string) or a
    manually mapped string output instead of basic Markdown collapsing layouts.
7.  **Multiline Input**: The chat input field in the frontend MUST support
    multiline text entry, allowing users to type longer queries before sending.
8.  **Dynamic Textarea Resizing**: The chat input `<textarea>` should
    dynamically resize its height to accommodate multiline input, improving the
    user experience for longer messages.
9.  **Theme Support**: The chat interface MUST fully support both dark and light
    themes. Ensure all components within the chat panel (e.g., message bubbles,
    input fields, background) have appropriate `dark:` variants for Tailwind CSS
    classes, consistent with the application's global theming.
10. **Robust API Error Handling**: Implement comprehensive `try-catch` blocks
    and error handling mechanisms for all API calls, especially around the
    streaming connections, to gracefully manage and report failures.

## Reference Implementations

The skill includes several reference implementations that you MUST review and
adapt when building the chat interface:

### Backend Setup (FastAPI or Node/Express)

When setting up your streaming chat endpoint, use one of the following:

- **Python / FastAPI**: `examples/fastapi_chat.py`
- **Node.js / Express**: `examples/express_chat.ts`

### Frontend Implementation (React)

You MUST maintain the conversation context array locally so follow-up questions
work. Review the comprehensive **streaming parser** reference implementation in:

- `examples/react_chat_panel.jsx`

## Validation Checklist

> [!CAUTION]
> If available, you MUST use browser testing capabilities (such as
> `browser_subagent`, Puppeteer, Playwright, or an equivalent available tool)
> to visually verify the frontend application is working correctly *before*
> notifying the user that the task is complete.

> [!IMPORTANT]
> You must include these items in whatever format you use to track your work
> (e.g., your task list, implementation plan, or internal checklist).

-   [ ] Is the chat interface functional and working correctly when asked a question?
-   [ ] Does it work with follow up questions?
-   [ ] Are the data sources correct?
-   [ ] Is the final response being rendered as markdown?
-   [ ] Are thoughts separate from the final response chat bubble?
-   [ ] Are thoughts streamed as they are generated and updating the UI to indicate progress?