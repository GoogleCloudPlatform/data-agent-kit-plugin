# Building with Streamlit

Follow these instructions when building data applications using the Streamlit framework.

## Required Dependencies
```
streamlit
plotly
pandas
numpy
```

## Page Configuration
You MUST call `st.set_page_config` first:
```python
st.set_page_config(
    page_title="App Name",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)
```

## Theme Toggle Pattern
```python
if "theme" not in st.session_state:
    st.session_state.theme = "light"

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

IS_DARK = st.session_state.theme == "dark"
```

## CSS Design System
Inject via `st.markdown(css, unsafe_allow_html=True)`.

### CSS Variables
Use f-strings with `IS_DARK` to swap values:
```css
:root {
    --bg: [dark: #09090b | light: #ffffff];
    --bg-subtle: [dark: #0c0c0f | light: #f9fafb];
    --card: [dark: #0c0c0f | light: #ffffff];
    --card-hover: [dark: #131316 | light: #f4f4f5];
    --border: [dark: #1e1e24 | light: #e4e4e7];
    --border-subtle: [dark: #16161a | light: #f0f0f2];
    --text: [dark: #fafafa | light: #09090b];
    --text-muted: #71717a;
    --text-dim: [dark: #52525b | light: #a1a1aa];
    --accent: #2563eb;
    --accent-muted: #1d4ed8;
    --green: [dark: #22c55e | light: #16a34a];
    --green-muted: [dark: rgba(34,197,94,0.12) | light: rgba(22,163,74,0.08)];
    --red: [dark: #ef4444 | light: #dc2626];
    --red-muted: [dark: rgba(239,68,68,0.12) | light: rgba(220,38,38,0.08)];
    --amber: [dark: #f59e0b | light: #d97706];
    --amber-muted: [dark: rgba(245,158,11,0.12) | light: rgba(217,119,6,0.08)];
    --shadow: [dark: none | light: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03)];
    --radius: 10px;
}
```

### Key CSS Classes

**Hide Streamlit chrome:**
```css
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"], .stDeployButton,
div[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}
```

**Global App Styling:**
```css
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container, section[data-testid="stMain"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', -apple-system, sans-serif !important;
}
.block-container {
    padding: 2rem 2.5rem 3rem !important;
    max-width: 1360px !important;
}
```

**Tabs (pill-style):**
```css
button[data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    font-size: 0.835rem !important;
    font-weight: 500 !important;
    padding: 0.55rem 1rem !important;
    border: 1px solid transparent !important;
    border-radius: 7px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--text) !important;
    background: var(--card) !important;
    border-color: var(--border) !important;
}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {
    display: none !important;
}
[data-baseweb="tab-list"] {
    gap: 4px !important;
    background: var(--bg-subtle) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 3px;
}
```

## Component Patterns

### Metric Card (KPI)
```python
def metric_card(label, value, delta=None, delta_type="up"):
    cls = f"delta-{delta_type}"
    arrow = "↑" if delta_type == "up" else ("↓" if delta_type == "down" else "→")
    delta_html = f'<div class="metric-delta {cls}">{arrow} {delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)
```
CSS:
```css
.metric-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem 1.4rem; box-shadow: var(--shadow); }
.metric-label { font-size: 0.78rem; color: var(--text-muted); font-weight: 500; }
.metric-value { font-size: 1.75rem; font-weight: 700; color: var(--text); letter-spacing: -0.03em; }
.metric-delta { font-size: 0.75rem; font-weight: 500; margin-top: 0.4rem; padding: 2px 8px; border-radius: 6px; display: inline-flex; align-items: center; gap: 3px; }
.delta-up { color: var(--green); background: var(--green-muted); }
.delta-down { color: var(--red); background: var(--red-muted); }
.delta-warn { color: var(--amber); background: var(--amber-muted); }
```

### Chart Container
Wrap every Plotly chart in a styled card:
```python
st.markdown("""
<div class="chart-wrap">
    <div class="chart-title">Chart Title</div>
    <div class="chart-subtitle">Description text</div>
""", unsafe_allow_html=True)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("</div>", unsafe_allow_html=True)
```
CSS:
```css
.chart-wrap { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.2rem 1.2rem 0.6rem; box-shadow: var(--shadow); }
.chart-title { font-size: 0.82rem; font-weight: 600; color: var(--text); }
.chart-subtitle { font-size: 0.72rem; color: var(--text-dim); margin-bottom: 0.8rem; }
```

### Data Table (HTML)
Use HTML tables with custom styling instead of `st.dataframe`:
```python
st.markdown(f"""
<table class="data-table">
    <thead><tr><th>Col1</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
</table>
""", unsafe_allow_html=True)
```
CSS:
```css
.data-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.8rem; }
.data-table th { text-align: left; padding: 0.6rem 0.8rem; color: var(--text-muted); font-weight: 500; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--border); }
.data-table td { padding: 0.65rem 0.8rem; color: var(--text); border-bottom: 1px solid var(--border-subtle); }
.data-table tr:last-child td { border-bottom: none; }
```

### Status Badges
```css
.badge { display: inline-block; padding: 2px 9px; border-radius: 6px; font-size: 0.72rem; font-weight: 500; }
.badge-green { color: var(--green); background: var(--green-muted); }
.badge-red { color: var(--red); background: var(--red-muted); }
.badge-amber { color: var(--amber); background: var(--amber-muted); }
.badge-blue { color: var(--accent); background: rgba(37,99,235,0.1); }
```

### Brand / Logo Header
```python
head_left, head_right = st.columns([8, 1])
with head_left:
    st.markdown("""
    <div class="brand">
        <span class="brand-name">App Name</span>
    </div>
    """, unsafe_allow_html=True)
with head_right:
    theme_label = "☀️ Light" if IS_DARK else "🌙 Dark"
    st.button(theme_label, on_click=toggle_theme, use_container_width=True)
```

## Plotly Chart Theming
Apply this layout to ALL charts:
```python
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#71717a" if not IS_DARK else "#a1a1aa", size=11),
    margin=dict(l=0, r=0, t=8, b=0),
    xaxis=dict(
        gridcolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        zerolinecolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        tickfont=dict(size=10, color="#71717a"),
    ),
    yaxis=dict(
        gridcolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        zerolinecolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        tickfont=dict(size=10, color="#71717a"),
    ),
)
```

## Layout Patterns

### Row of KPIs
```python
c1, c2, c3, c4 = st.columns(4)
with c1: metric_card("Label", "Value", delta="Change", delta_type="up")
```

### Column gap CSS
```css
[data-testid="stHorizontalBlock"] { gap: 1.25rem !important; }
[data-testid="stVerticalBlock"] > div:has(> [data-testid="stHorizontalBlock"]) {
    margin-bottom: 0.5rem !important;
}
```

## Checklist for New Dashboards
1. Set page config (wide layout, collapsed sidebar)
2. Add theme toggle state
3. Inject full CSS block with theme-aware variables
4. Define `styled_chart()` and `metric_card()` helpers
5. Build header with brand + theme toggle
6. Use `st.tabs()` for navigation
7. Wrap every chart in `<div class="chart-wrap">` with title/subtitle
8. Use HTML tables with `.data-table` class
9. Use `.badge` spans for status indicators
10. Always `config={"displayModeBar": False}` on plotly charts
