# Styling and Data Patterns for Shiny for Python

This reference covers the non-widget parts of a polished dashboard: project structure, data loading, number formatting, CSS, and light or dark presentation choices.

## Project Structure

Use a small, predictable structure for dashboard apps.

```text
my-dashboard/
├── app-core.py
├── app-express.py
├── shared.py
├── plots.py
├── data.csv
└── requirements.txt
```

Guidelines:

- Keep one runnable app file per API style.
- Put data loading, reusable constants, and `app_dir` in `shared.py`.
- Move complex chart construction into `plots.py` or another helper module once a render function becomes hard to scan.
- Keep CSS overrides small and intentional.

## Data Loading

Load static data once at module scope or in `shared.py`.

```python
from pathlib import Path

import pandas as pd

app_dir = Path(__file__).parent
df = pd.read_csv(app_dir / "data.csv")

metric_columns = ["price", "rating", "reviews"]
neighborhood_choices = sorted(df["neighborhood"].dropna().unique())
```

This keeps reactive code focused on filtering and rendering instead of repeated file I/O.

### Clean data before it reaches plots

For dashboard inputs and charts, normalize types early:

```python
df["price"] = pd.to_numeric(df["price"], errors="coerce")
df["score_rating"] = pd.to_numeric(df["score_rating"], errors="coerce")
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
df = df.dropna(subset=["latitude", "longitude"])
```

Guidelines:

- Coerce mixed-type numeric columns with `errors="coerce"`.
- Drop invalid map coordinates up front.
- Fill or label missing categorical values before exposing them in inputs.
- Precompute choice lists and slider ranges once.

## Number Formatting

Dashboard text should be formatted before it reaches a value box, annotation, or table summary.

```python
def fmt_currency(amount: float) -> str:
    return f"${amount:,.0f}"


def fmt_percent(ratio: float) -> str:
    return f"{ratio:.1%}"


def fmt_large(number: float) -> str:
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{number:,.0f}"
```

Avoid raw values like `12345.6789` or `0.873421` in user-facing UI.

## Themes and brand palette

The single biggest visual upgrade for a Python Shiny dashboard is shipping an explicit light theme and a small brand palette. Default bslib styling reads as stock Shiny.

```python
import shinyswatch
from shiny import ui

BRAND_COLORS = {
    "primary":   "#0d6efd",
    "secondary": "#6c757d",
    "success":   "#198754",
    "warning":   "#ffc107",
    "danger":    "#dc3545",
    "accent":    "#6610f2",
}

# Reuse this ordered list anywhere you need a categorical color sequence
# (Plotly, Matplotlib, lonboard, great_tables data_color).
BRAND_SEQUENCE = [
    BRAND_COLORS["primary"],
    BRAND_COLORS["success"],
    BRAND_COLORS["warning"],
    BRAND_COLORS["danger"],
    BRAND_COLORS["accent"],
]

app_ui = ui.page_navbar(
    ...,
    title="Analytics Platform",
    theme=shinyswatch.theme.zephyr,
    fillable=False,
)
```

Guidelines:

- Always pass an explicit `theme=` to your `ui.page_*()` call. Prefer `shinyswatch.theme.zephyr`, `flatly`, `minty`, `cosmo`, `lumen`, or `yeti`.
- Do not add `ui.input_dark_mode()` to dashboards. Ship a polished light theme instead.
- Define `BRAND_COLORS` and `BRAND_SEQUENCE` once in `shared.py` and reuse them across Plotly templates, Matplotlib charts, value-box themes, and `great_tables.data_color()` ramps.
- Use named Bootstrap themes (`"primary"`, `"success"`, `"info"`, `"warning"`, `"danger"`) on value boxes so they line up with the active swatch.
- Avoid mixing rainbow palettes with the brand sequence — pick one and stick to it.

## CSS and Theming

Prefer inline `ui.tags.style()` over a separate `styles.css` file. A missing
external stylesheet crashes the app at startup and is the most common agent
failure mode.

```python
from shiny import ui

app_ui = ui.page_sidebar(
    ui.tags.style("""
        .bslib-grid {
          gap: 1rem !important;
          row-gap: 1rem !important;
          column-gap: 1rem !important;
        }
        .bslib-page-fill > .card + .card,
        .bslib-page-fill > .bslib-grid + .bslib-grid,
        .bslib-page-fill > .card + .bslib-grid,
        .bslib-page-fill > .bslib-grid + .card,
        .bslib-page-sidebar__main > .card + .card,
        .bslib-page-sidebar__main > .bslib-grid + .bslib-grid,
        .bslib-page-sidebar__main > .card + .bslib-grid,
        .bslib-page-sidebar__main > .bslib-grid + .card {
          margin-top: 1rem;
        }
    """),
    ...,
)
```

### Card-spacing safety net

The CSS above is the mandatory card-spacing safety net. Unlike R bslib,
Python Shiny's `ui.layout_columns()` and `ui.layout_column_wrap()` render
`<div class="bslib-grid">` with `gap: 0` by default unless `gap=` is passed
explicitly. This inline style block catches the most common visual defect:
cards rendered edge-to-edge with no spacing.

Use CSS only for:

- spacing and alignment helpers
- custom card or hero section styling
- subtle borders, backgrounds, and typography rules
- responsive tweaks that do not belong inside Python layout logic

Avoid using CSS to rebuild the layout system from scratch when Shiny layout primitives already solve the problem.


### Theme direction

Shiny for Python does not use the same `bs_theme()` object as bslib in R, so keep the theme story practical:

- use named Bootstrap colors consistently across value boxes and accents
- define a small set of CSS custom properties for brand colors if the app needs a distinct look
- avoid mixing many unrelated accent colors across cards and charts
- if the app needs color-mode switching, use `ui.input_dark_mode()` intentionally rather than adding large unrelated CSS overrides

```python
ui.input_dark_mode(id="mode")
```

## Requirements

Include the packages your dashboard actually uses. Common dashboard requirements are:

```text
shiny
pandas
plotly
matplotlib
seaborn
faicons
shinywidgets
```

Add mapping or table packages only when the app needs them.

## Best Practices

1. Load data once and reuse it through reactive calcs.
2. Clean numeric and coordinate columns before they hit inputs or plots.
3. Keep formatting helpers near the data layer, not scattered across render functions.
4. Use `ui.tags.style(...)` for small style layers to avoid missing-file startup crashes.
5. Treat dark mode as an explicit product choice, not a side effect of random CSS overrides.
