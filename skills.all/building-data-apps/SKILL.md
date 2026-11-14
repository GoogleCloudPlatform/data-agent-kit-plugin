---
name: building-data-apps
description: |
  Build modern data apps, dashboards, and interactive reports using either
  React + Vite or Streamlit. Includes optional Gemini Data Analytics chat
  integration for an AI powered "chat with your data" experience.

  Relevant when any of the following conditions are true:
    1. User explicitly requests to build a data dashboard, data application, or visualization UI, and the UI pulls data from a GCP database (defaulting to BigQuery unless otherwise specified).
    2. You need to generate a frontend web application to interact with, query, and visualize data from GCP data sources.
    3. User wants to build a "chat with your data" experience or integrate the Gemini Data Analytics chat API into a web interface.

  Do NOT use when any of the following conditions are true:
    1. The request is for building backend-only services.
    2. The request is for simple CLI scripts or command-line applications.
    3. The web application is not data-centric or does not involve visualizing/querying data from GCP sources.
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# Building Data Applications

Architect high-quality data dashboards and interactive reports. You MUST select
the appropriate framework before implementation.

## Step 0: Framework Selection

You MUST select the framework based on the user's maintenance requirements and
data ecosystem.

### Choice: Streamlit

-   **User Profile**: Data Scientists / Python users.
-   **Logic Complexity**: High Python dependency (Pandas, NumPy, local data
    processing).
-   **Deployment**: Single-file Python script.
-   **Customization**: Standard layout (fast boilerplate).

### Choice: React + Vite

-   **User Profile**: Web Developers / Full-stack teams.
-   **Logic Complexity**: High UI and Interactivity requirements (e.g.,
    drag-and-drop, interactive maps).
-   **Deployment**: Standalone Frontend + Backend API.
-   **Customization**: Infinite (Custom CSS, specialized JS libraries).

### Guidance:

-   **Check for existing stack first**: ALWAYS prefer the framework the user is
    already using in their project (e.g., if you see a `package.json` with React
    dependencies, use React; if you see existing Streamlit files, use
    Streamlit).
-   **Default to React + Vite** for production-grade applications that require
    complex client-side state, custom branding, or integration into a larger web
    ecosystem.
-   **Default to Streamlit** if the user specifically mentions "Python
    dashboard", needs to iterate on complex local Python data processing, or
    requires a single-script deployment.

## Step 1: Implementation Plan

You MUST propose a plan to the user that specifies the chosen framework and
justifies the choice based on the criteria above.

--------------------------------------------------------------------------------

## Shared Design Standards

Regardless of framework, you MUST follow the principles in
`references/shared_design_system.md`.

-   **Visual Style**: Minimal chrome, zinc color palette, and card-based
    layouts.
-   **Typography**: `DM Sans` for content, `JetBrains Mono` for data.

--------------------------------------------------------------------------------

## Framework Implementation

### If using Streamlit:

1.  Read `references/streamlit_framework.md` for detailed CSS and component
    patterns.
2.  Follow the "Checklist for New Dashboards" in that file.

### If using React + Vite:

1.  Read `references/react_framework.md` for Tailwind and ECharts setup.
2.  Follow the detailed component guidelines for KPI cards, Tables, and Panels.

--------------------------------------------------------------------------------

## AI Chat Interface (Optional Feature)

```
> [!IMPORTANT]
>
> If the user does not explicitly request a chat interface, you SHOULD
> proactively ask them: "Would you like to include a Gemini-powered chat
> interface to enable natural language queries against your data?" OR if
> there is an implementation plan: "Would you like to include a
> Gemini-powered chat interface to enable natural language queries against
> your data? Let me know and I'll update the plan!".
```

If the user requests or agrees to the chat interface:

```
> [!CAUTION]
>
> Adding the chat interface is a significant change. Implicit approval of
> the implementation plan for including the chat interface MUST never be
> assumed.
```

1.  **Gather Technical Details**: You MUST read `references/chat_integration.md`
    for the technical requirements.
2.  **Update the implementation plan**: If and only if there is an
    implementation plan, you MUST update the implementation plan. This is a
    significant change so the user must explicitly approve the updated plan.
3.  **Verify Prerequisites**: Ensure the user has the Gemini Data Analytics API
    enabled and data exists in BigQuery.
4.  **Reference Examples**: Adapt the patterns in
    `examples/react_chat_panel.jsx` and either `examples/fastapi_chat.py` or
    `examples/express_chat.ts`.

## Acceptance Criteria

> [!CAUTION]
>
> If available, you MUST use browser testing capabilities (such as
> `browser_subagent`, Puppeteer, Playwright, or an equivalent available tool) to
> visually verify the frontend application is working correctly *before*
> notifying the user that the task is complete.

> [!IMPORTANT]
>
> The following checklist represents the strict requirements for this task. You
> must include these items in whatever format you use to track your work (e.g.,
> your task list, implementation plan, or internal checklist).

-   [ ] Are CSS hover transitions smooth?
-   [ ] Are date fields formatted readably? (e.g., `MMM dd, yyyy`)
-   [ ] Do z-indexes stack correctly so dropdowns appear above table headers?
    (`relative z-30`)
-   [ ] Do all interactive form/button inputs handle loading/disabled states?
-   [ ] Is the application responsive and does the layout adapt well to
    different screen sizes?
-   [ ] Are API calls for data fetching successful, and is there appropriate
    error handling?
-   [ ] Does the dark mode toggle function correctly and apply styles
    consistently?
-   [ ] Do all visualizations render correctly and are they interactive where
    expected?
-   [ ] Is the dashboard visually appealing?
