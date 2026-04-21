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
├── styles.css
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

## CSS and Theming

Use a small stylesheet for layout polish and component-specific tuning.

```python
from pathlib import Path
from shiny import ui

app_dir = Path(__file__).parent

app_ui = ui.page_sidebar(
    ui.include_css(app_dir / "styles.css"),
    ...,
)
```

Use CSS for:

- spacing and alignment helpers
- custom card or hero section styling
- subtle borders, backgrounds, and typography rules
- responsive tweaks that do not belong inside Python layout logic

### Mandatory card-spacing safety net

Always include this rule in `styles.css` so cards never appear glued together,
even when a `gap` argument is forgotten on a layout container. Unlike R bslib,
Python Shiny's `ui.layout_columns()` and `ui.layout_column_wrap()` render
`<div class="bslib-grid">` with `gap: 0` by default unless `gap=` is passed
explicitly, so this CSS is the most reliable defense:

```css
/* Force a sensible default gap on every bslib grid container.
   Inline style="gap: ..." from layout_columns(gap=...) still wins. */
.bslib-grid {
  gap: 1rem !important;
  row-gap: 1rem !important;
  column-gap: 1rem !important;
}

/* Vertical spacing between bare cards or between a card and the next
   layout row when they are placed as direct page children. */
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

/* Value boxes inside a bslib grid never touch */
.bslib-grid > .bslib-value-box + .bslib-value-box {
  margin-left: 0;  /* gap on parent already handles spacing */
}
```

This safety net is **mandatory** for every Python Shiny dashboard. It catches
the most common visual defect: cards rendered edge-to-edge with no spacing
because `gap=` was omitted on a layout container or because cards were placed
as bare page children. It does not replace passing `gap="1rem"` explicitly —
it ensures the dashboard looks correct even if you forget.

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
4. Use `ui.include_css(...)` for small style layers instead of large inline `<style>` blocks.
5. Treat dark mode as an explicit product choice, not a side effect of random CSS overrides.
