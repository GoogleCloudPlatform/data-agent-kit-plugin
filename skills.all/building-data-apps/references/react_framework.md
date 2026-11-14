# Building with React + Vite

Follow these instructions when building data applications using the React framework with Vite.

## Technology Stack

-   **Framework:** React in Vite
-   **Styling:** Tailwind CSS (Dark Mode by default)
-   **Icons:** `lucide-react`
-   **Date Formatting:** `date-fns`
-   **Data Fetching:** Axios (REST API calls)
-   **Drag & Drop:** `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`
    (Used for sortable lists/swatches)
-   **Data Visualization:** `echarts` and `echarts-for-react`

## Global Visuals & Theming

-   **Backgrounds:** The app must support both Light and Dark modes. Always map
    colors to their `dark:` variant and provide a light mode equivalent.
    -   Page Background: `bg-zinc-50 dark:bg-[#09090b]`
    -   Cards / Containers: `bg-white dark:bg-[#0c0c0f]` (solid slightly lighter
        dark)
-   **Typography:** Use sans-serif default fonts.
    -   Primary text (headings, important data): `text-zinc-950
        dark:text-zinc-50`
    -   Secondary text (labels, dates, table headers): `text-zinc-500
        dark:text-zinc-400`
    -   Borders: Subtle separators `border-zinc-200 dark:border-zinc-800`
    -   Rounded corners: Containers should use `rounded-xl`, inner graphical
        bars should use `rounded-sm` or `rounded-md`.
-   **Theme Toggle:** Provide a simple Sun/Moon toggle icon button in the header
    that switches the HTML class `dark` on and off.

## Layout Hierarchy

The application should follow a clean dashboard layout:

1. **Header Row:** A top
title aligned left, theme toggle aligned right. `max-w-[1600px] mx-auto p-6`.
2. **KPI Cards Row:** A horizontal grid (`grid-cols-4` or `grid-cols-1
md:grid-cols-4`) of summary statistics.
3. **Main Content Split:** A flex container containing a prominent primary element (e.g., a Data Table) and a
conditional secondary panel (e.g., an Investigation/Details Panel).

  - *State Normal:* Table takes `w-full`.
  - *State Selected:* Table shrinks to `w-2/3`, side panel slides/fades in as `w-1/3`. Add `transition-all duration-300` to make the shift smooth.

## Components

### 1. KPI Cards

-   Should have a subtle border (`border-zinc-200 dark:border-zinc-800`).
-   Display a small icon (e.g., a trend arrow or lucide icon) next to a large
    numeric value.
-   Small text labels for the value title (`text-zinc-500 dark:text-zinc-400`).
-   **Trend Indicator:** Should use a pill-style background based on value:
    `bg-emerald-100 text-emerald-700` and `dark:bg-emerald-900/30
    dark:text-emerald-400` for positive trends. Negative trends should use
    `bg-rose-100 dark:bg-rose-900/30` equivalents. Include small embedded trend
    arrows.

### 2. Primary Data Table

-   **Container:** The table container should be `bg-white dark:bg-zinc-900
    border border-zinc-200 dark:border-zinc-800 rounded-[12px]
    overflow-hidden`.
-   **Toolbar:** Above the table, place filtering actions (e.g., "Filter",
    "Date") as dropdown buttons.
    -   *Filtering Logic:* Do not delete raw data when filtering. Use local
        component state to map/filter visibility based on the selected dropdown
        criteria.
-   **Header:** Sticky table header (`sticky top-0 bg-zinc-100
    dark:bg-zinc-900 z-10 text-zinc-500 dark:text-zinc-400`).
-   **Rows:** Standard rows (`text-zinc-900 dark:text-zinc-200 border-b
    border-zinc-100 dark:border-zinc-800`). Add hover effects
    (`hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer
    transition-colors`).
-   **Selection State:** Active row should have distinct highlight (e.g.,
    `bg-blue-50 dark:bg-blue-900/40 hover:bg-blue-100
    dark:hover:bg-blue-900/60`).
-   **Visual Indicators (Sparklines):** For numeric scores or risk values, use
    horizontal progress bars instead of raw text pills.
    -   Track color: `bg-zinc-700` (dark gray)
    -   Fill colors: `bg-emerald-500` (low risk), `bg-orange-400` (medium),
        `bg-rose-500` (high risk). Add inline `style={{ width: score + "%" }}`
        logic.
-   **Pagination Controls:** Place at the bottom border area.
    -   Restrict table height optionally, or set pagination limits to roughly 30
        rows.
    -   Exclusively use icon-only buttons for pagination text labels
        (`ChevronsLeft` for First Page, `ChevronLeft` for Previous,
        `ChevronRight` for Next, `ChevronsRight` for Last).
    -   Style disabled states visually (`disabled:opacity-50
        disabled:cursor-not-allowed`) so users clearly know when they are on the
        first or last page.

### 3. Investigation/Details Side Panel

-   Should appear to the right of the table when a row is clicked.
-   Includes a close "X" button at the top right to dismiss it.
-   **Details Section:** Use small stacked labels and visually distinct blocks
    (e.g., Merchant info, Amount, Customer limits) styled with `bg-zinc-800
    border-zinc-700 rounded-md p-3`.
-   **Action Buttons:** At the bottom or middle, place primary and secondary
    action buttons (e.g., "Approve" `bg-emerald-500`, "Reject" `bg-rose-500`
    text white). Update parent state so the table reflects the action instantly.

### 4. Typography & Text

-   Use standardized semantic HTML tags and styling.
-   **Headings:** `text-zinc-950 dark:text-zinc-50` with `tracking-tight`.
    `h1` is `text-4xl font-extrabold`, down to `h6` being `text-sm font-semibold
    uppercase tracking-wider text-zinc-500`.
-   **Body:** `text-zinc-500 dark:text-zinc-400`.
-   **Specialty:** Mono-spaced text for IDs (`font-mono text-zinc-500
    bg-zinc-100 dark:bg-zinc-800 rounded px-1.5`).

### 5. Inputs & Controls

-   **Buttons:**
    -   Primary: `bg-[#059669] hover:bg-[#047857] text-[#000000] rounded-[8px]
        px-[16px] py-[8px] font-[500] transition-colors shadow-sm`.
    -   Secondary: `bg-[#ffffff] dark:bg-[#262626] hover:bg-[#f8fafc]
        dark:hover:bg-zinc-800 text-[#334155] dark:text-zinc-200 border
        border-zinc-200 dark:border-zinc-700 rounded-[8px] px-[16px] py-[8px]
        font-[500] transition-colors shadow-sm`.
    -   Destructive: `bg-[#e11d48] hover:bg-[#be123c] text-[#ffffff]
        rounded-[8px] px-[16px] py-[8px] font-[500] transition-colors
        shadow-sm`.
    -   Ghost: `text-[#2563eb] dark:text-[#60a5fa] hover:bg-[#eff6ff]
        dark:hover:bg-[#1e3a8a] rounded-[8px] px-[16px] py-[8px] font-[500]
        transition-colors bg-transparent border border-transparent shadow-none`.
-   **Inputs:** `w-full bg-[#ffffff] dark:bg-[#09090b] border border-zinc-200
    dark:border-zinc-800 rounded-[8px] px-[12px] py-[8px] text-sm shadow-sm
    focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500
    text-zinc-950 dark:text-zinc-100 transition-all`. Provide a `label` with
    `text-xs font-medium text-zinc-500 mb-1.5`.
-   **Controls (Checkboxes/Radios/Toggles):** Standardize accent color to
    `blue-500`.
-   **Segmented Controls:** Use a pill-shaped container `bg-zinc-100
    dark:bg-[#0c0c0f] p-1 rounded-[8px]` with active states having a `bg-white
    dark:bg-zinc-800 text-[#2563eb] dark:text-[#60a5fa]` style and shadow.

### 6. Navigation & Overlays

-   **Tabs:** Underline-style tabs. Active tab: `border-b-2 border-[#3b82f6]
    text-[#2563eb] dark:text-[#60a5fa]`. Inactive tab: `text-zinc-500
    hover:text-[#334155] dark:hover:text-[#e2e8f0] transparent border-b-2
    hover:border-[#3b82f6]`.
-   **Dialogs/Modals:** Centered overlay with a backdrop `bg-zinc-950/50
    backdrop-blur-sm`. Modal surface: `bg-[#ffffff] dark:bg-[#0c0c0f]
    rounded-[12px] border border-zinc-200 dark:border-zinc-800 shadow-xl
    w-full max-w-md p-6`.
-   **Dropdown Menus:** Absolute positioned, floating menu `bg-[#ffffff]
    dark:bg-[#0c0c0f] shadow-lg border border-zinc-200 dark:border-zinc-800
    rounded-[12px] py-1`.

### 7. Feedback & Status

-   **Alerts:** Colored containers `bg-{color}-50 dark:bg-{color}-900/20 border
    border-{color}-200 dark:border-{color}-800/30 text-{color}-800
    dark:text-{color}-300 rounded-lg p-4 flex gap-3`. (Colors: emerald for
    success, rose for error, amber for warning, blue for info).
-   **Loaders:** Skeleton pulse loaders `animate-pulse bg-zinc-200
    dark:bg-zinc-800 rounded`. Circular SVG spinners for loading.

### 8. Data Visualization (Apache ECharts)

-   Do NOT try to build complex charts from scratch with divs/Tailwind.
-   Use `echarts` and `echarts-for-react`.
-   **Base Theme Integration:** Provide a standardized config object: `color`
    arrays, `textStyle: { fontFamily: "Inter, sans-serif" }`, dark mode
    compatible tooltips `backgroundColor: "rgba(255, 255, 255, 0.95)"`,
    `borderColor: "#e2e8f0"`, `textStyle: { color: "#0f172a" }`, and sensible
    grid paddings.
-   **Container Styling:** Housed inside `bg-white dark:bg-[#0c0c0f] rounded-xl
    border border-zinc-200 dark:border-zinc-800 shadow-sm`.
-   **Layout Constraints:** Analytical charts should generally be presented
    large for readability, enforcing a strict **1 Chart Per Row** design pattern
    (`grid-cols-1`) when placed inside main content sections or galleries. Do
    not squish them.
-   **Detail Orientation:** Dashboards should be designed to provide in-depth
    insights. Include multiple related charts, filtering options, and drill-down
    capabilities where appropriate to ensure the dashboard is comprehensive and
    not just a high-level overview. Go beyond surface level results to present
    meaningful insights.

#### 9. Global State & Sortable Components (Sortable UI)

-   To build sortable, interactive interfaces (e.g. reorderable swatches or
    lists), strictly use `@dnd-kit/core` and `@dnd-kit/sortable`.
-   Use a `Context` provider pattern when state applies across multiple sibling
    components (like customizing app-wide chart colors and rendering an
    interactive drag-and-drop sortable swatch component).
-   Follow standard DND Kit setup: wrap in `<DndContext onDragEnd={...}>`, wrap
    sortables in `<SortableContext items={items} strategy={...}>`, and bind the
    children elements with `useSortable({ id })`.
-   **Standard Chart Colors Array:** Establish these 10 Tailwind standard
    500-level variables when initiating chart sets: `["#3b82f6", "#10b981",
    "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16", "#f97316",
    "#6366f1"]`.
