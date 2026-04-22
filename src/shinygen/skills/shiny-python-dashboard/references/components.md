# Components for Shiny for Python Dashboards

This reference covers the card-level building blocks of a Shiny for Python dashboard: cards, value boxes, accordions, and lightweight contextual UI such as tooltips and popovers.

## Cards

Cards are the default container for dashboard content.

```python
ui.card(
    ui.card_header("Revenue by month"),
    ui.output_plot("revenue_plot"),
    ui.card_footer("Updated daily at 6am"),
    full_screen=True,
)
```

Use cards for:

- charts
- tables
- maps
- summaries that need supporting text
- module-like dashboard sections

Guidelines:

- Add `ui.card_header()` to every card.
- Default to `full_screen=True` for charts, maps, and tables.
- Give visualization cards a floor like `min_height="320px"` so charts stay readable.
- Use a larger floor such as `min_height="420px"` for detailed tables.
- Do not place more than 2 medium or large visualization cards in a row.
- Use `ui.card_footer()` for provenance, notes, or small actions.
- Keep static text cards shorter than plot cards; large paragraphs belong in scrolling pages, not dashboard grids.

### Preventing squished dashboards

When a dashboard has a KPI row plus multiple rows of charts, maps, or tables, prefer a scrolling page over a fully fillable one.

- Use `fillable=False` for dense dashboards.
- Keep KPI rows in `ui.layout_column_wrap(..., width="240px", fill=False)`.
- Give each chart or map card `min_height="320px"` or more.
- Split crowded content across tabs or pages instead of forcing many shallow cards into one viewport.

### Card headers with inline controls

Card headers can hold small secondary controls.

```python
ui.card_header(
    "Bill vs tip",
    ui.popover(
        icon_svg("ellipsis"),
        ui.input_radio_buttons("color_var", None, ["none", "sex", "day"], inline=True),
        title="Color by",
        placement="top",
    ),
    class_="d-flex justify-content-between align-items-center",
)
```

Use this for secondary options that do not deserve a full sidebar section.

## Value Boxes

Use `ui.value_box()` for KPIs and headline metrics.

**Core API:**

```python
ui.layout_column_wrap(
    ui.value_box(
        "Total users",
        ui.output_ui("total_users"),
        showcase=icon_svg("users"),
        theme="primary",
    ),
    ui.value_box(
        "Average order",
        ui.output_ui("avg_order"),
        showcase=icon_svg("wallet"),
        theme="success",
    ),
    width="240px",
    fill=False,
)
```

**Express API:**

```python
with ui.layout_columns(fill=False):
    with ui.value_box(showcase=icon_svg("users"), theme="primary"):
        "Total users"

        @render.express
        def total_users():
            f"{len(df):,}"
```

Guidelines:

- Keep the row to 3 or 4 boxes.
- Prefer `ui.layout_column_wrap(..., width="240px", fill=False)` so KPI cards wrap before becoming cramped.
- Use named themes like `"primary"`, `"success"`, `"info"`, `"warning"`, and `"danger"`.
- Use icons that reinforce the metric; do not use emojis.
- Format the displayed value instead of passing a raw float or integer.

### Dynamic showcase icons

Use `@render.ui` when the icon depends on the data.

```python
@render.ui
def change_icon():
    icon = icon_svg("arrow-up" if get_change() >= 0 else "arrow-down")
    icon.add_class("text-success" if get_change() >= 0 else "text-danger")
    return icon
```

In Express, `with ui.hold():` is useful when an output is referenced before it is defined.

### KPI value box with period-over-period delta

Headline metrics read better with a small "vs prior period" delta. Render the delta as a high-contrast pill so it stays legible on colored or gradient value-box backgrounds. Never rely on raw Bootstrap `text-success` / `text-danger` inside themed value boxes — they wash out.

```python
from faicons import icon_svg
from shiny import ui


def value_box_with_delta(title, value, delta_pct, *, showcase, theme="primary"):
    """Value box with a pill-style period-over-period delta."""
    up = delta_pct >= 0
    arrow = icon_svg("arrow-up" if up else "arrow-down")
    pill_bg = "rgba(25, 135, 84, 0.18)" if up else "rgba(220, 53, 69, 0.18)"
    pill_fg = "#0f5132" if up else "#842029"
    pill = ui.span(
        arrow,
        f" {abs(delta_pct):.1f}% vs prior period",
        style=(
            f"background:{pill_bg};color:{pill_fg};"
            "padding:2px 8px;border-radius:999px;"
            "font-size:0.8rem;font-weight:600;display:inline-flex;"
            "align-items:center;gap:4px;margin-top:6px;"
        ),
    )
    return ui.value_box(title, value, pill, showcase=showcase, theme=theme)
```

Guidelines:

- Always pair the headline number with context (delta, target, or share).
- Format the value before passing it in — never show raw floats.
- Keep the pill copy short; one metric, one comparison.
- Use the same delta convention (vs prior period, vs target, etc.) across the whole dashboard.

## Summary tables with `great_tables`

Use `great_tables.GT(...)` for short, presentation-quality summary tables — leaderboards, KPI breakdowns, executive rollups. Reach for `render.DataGrid` only when users need to sort or filter long tables.

```python
from great_tables import GT, md, style, loc
from shiny import render


@render.ui
def revenue_summary():
    summary = (
        filtered_data()
        .groupby("region", as_index=False)
        .agg(revenue=("revenue", "sum"), orders=("order_id", "nunique"))
        .sort_values("revenue", ascending=False)
    )
    return (
        GT(summary)
        .tab_header(title="Revenue by region", subtitle=md("Last 30 days"))
        .fmt_currency(columns="revenue", currency="USD", decimals=0)
        .fmt_integer(columns="orders")
        .data_color(
            columns="revenue",
            palette=["#e7f1ff", "#0d6efd"],
        )
        .cols_label(region="Region", revenue="Revenue", orders="Orders")
        .tab_options(
            table_font_size="0.9rem",
            heading_title_font_size="1.05rem",
            column_labels_font_weight="600",
            table_border_top_style="hidden",
        )
        .as_raw_html()
    )
```

Wire it into the UI with `ui.output_ui("revenue_summary")` inside a card.

Guidelines:

- Keep `GT` tables short — typically under 25 rows. For longer tables, switch to `render.DataGrid`.
- Always set a `tab_header()` so the table reads as a finished artifact.
- Format every numeric column (`fmt_currency`, `fmt_percent`, `fmt_integer`, `fmt_number`).
- Use a single soft `data_color` ramp on the most important column instead of coloring every column.
- Rename columns with `cols_label()` so headers are human-readable.
- Return `.as_raw_html()` and render through `@render.ui`.

## Accordions

Accordions are most useful in sidebars with many controls.

```python
ui.sidebar(
    ui.accordion(
        ui.accordion_panel(
            "Filters",
            ui.input_selectize("species", "Species", choices=species),
            ui.input_date_range("dates", "Dates", start=start, end=end),
        ),
        ui.accordion_panel(
            "Display",
            ui.input_switch("show_trend", "Show trend", value=True),
            ui.input_slider("bins", "Bins", min=5, max=50, value=20),
        ),
        open=["Filters"],
    ),
    open="desktop",
)
```

Use accordions when:

- the sidebar has more than a handful of inputs
- some controls are clearly advanced or optional
- you want to reduce visual clutter on smaller screens

Keep related inputs together and leave only the most important panel open by default.

## Tooltips and Popovers

Tooltips provide quick read-only help. Popovers hold small interactive controls.

```python
ui.tooltip(
    icon_svg("circle-info", title="More information", a11y="sem"),
    "Shows how the metric is calculated",
)
```

```python
ui.popover(
    icon_svg("gear", title="Chart options", a11y="sem"),
    ui.input_select("palette", "Palette", choices=palettes),
    ui.input_switch("show_trend", "Show trend line", value=True),
    title="Chart options",
)
```

Guidelines:

- Use tooltips for one short explanation.
- Use popovers for 2 to 4 small controls.
- Give icon-only triggers accessible titles so screen readers have a useful label.
- Do not use popovers as a substitute for a real form or a full advanced-settings workflow.

## Toast-like Feedback

Use the framework's notification helpers for lightweight success, warning, or error feedback instead of permanently allocating screen space to ephemeral status messages.

Guidelines:

- Use notifications for completion, failure, or "export started" states.
- Keep them specific instead of saying only "Done".
- Reserve persistent on-page status areas for information users need to keep reading.

## Best Practices

1. Treat cards as the default dashboard container.
2. Use value boxes for headline metrics, not for long explanations.
3. Keep chart options in card-header popovers when they are secondary.
4. Group busy sidebars with accordions.
5. Give icon-only triggers accessible titles.
6. Avoid card-within-card compositions unless you are intentionally creating a nested layout.
