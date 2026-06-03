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
- Keep static text cards shorter than plot cards.
- **Fill Behavior**: Outputs (like plots, maps, and data grids) placed directly inside `ui.card_body()` automatically resize to fill the card's height. Let layout containers determine heights when grouping cards.

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

### Tabbed Cards

Use `ui.navset_card_underline()` or `ui.navset_card_pill()` to create cards with internal tabs.

**Express API:**
```python
with ui.navset_card_underline(title="Project Status"):
    with ui.nav_panel("Overview"):
        "Overview content"
    with ui.nav_panel("Team"):
        "Team list"
```

**Core API:**
```python
ui.navset_card_underline(
    ui.nav_panel("Overview", "Overview content"),
    ui.nav_panel("Team", "Team list"),
    title="Project Status",
)
```

### Cards with Sidebars

Use `ui.layout_sidebar()` and `ui.sidebar()` inside a card to create a local, card-scoped sidebar layout for filtering or configuring the card's specific visualization.

**Express API:**
```python
with ui.card(full_screen=True, height="400px"):
    ui.card_header("Flower Data Explorer")
    with ui.layout_sidebar():
        with ui.sidebar():
            ui.input_select("color_filter", "Color", ["All", "Red", "Yellow"])
            ui.input_slider("rows", "Rows", 1, 8, 5)
        with ui.card_body():
            ui.output_data_frame("flower_table")
```

**Core API:**
```python
ui.card(
    ui.card_header("Flower Data Explorer"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("color_filter", "Color", ["All", "Red", "Yellow"]),
            ui.input_slider("rows", "Rows", 1, 8, 5),
        ),
        ui.card_body(
            ui.output_data_frame("flower_table"),
        ),
    ),
    full_screen=True,
    height="400px",
)
```

### Toolbars (Shiny ≥ 1.6)

Use `ui.toolbar()` to embed compact controls inside `ui.card_header()`, `ui.card_footer()`, input labels, or `ui.input_submit_textarea(toolbar=...)`. This scopes controls to a single card instead of pushing more inputs into the global sidebar.

A card with several chart/table cards should normally include at least one or two toolbars: one for local chart display options and one for table/map actions. This makes the UI feel deliberate and keeps the global sidebar focused on filters that affect the whole page.

#### UI Express Code Example

```python
from faicons import icon_svg
from shiny.express import input, render, ui

with ui.card(full_screen=True):
    with ui.card_header():
        "Data View"
        with ui.toolbar(align="right"):
            ui.toolbar_input_select(
                id="view_mode",
                label="View Mode",
                choices=["Table", "Chart", "Map"],
                icon=icon_svg("eye"),
                show_label=True,
            )
            ui.toolbar_divider()
            ui.toolbar_input_select(
                id="filter_status",
                label="Filter Status",
                choices=["All", "Active", "Archived"],
                icon=icon_svg("filter"),
            )

    @render.text
    def selected_view():
        return f"View Mode: {input.view_mode()}, Filter: {input.filter_status()}"
```

#### UI Core Code Example

```python
from faicons import icon_svg
from shiny import App, render, ui

app_ui = ui.page_fixed(
    ui.card(
        ui.card_header(
            "Data View",
            ui.toolbar(
                ui.toolbar_input_select(
                    id="view_mode",
                    label="View Mode",
                    choices=["Table", "Chart", "Map"],
                    icon=icon_svg("eye"),
                    show_label=True,
                ),
                ui.toolbar_divider(),
                ui.toolbar_input_select(
                    id="filter_status",
                    label="Filter Status",
                    choices=["All", "Active", "Archived"],
                    icon=icon_svg("filter"),
                ),
                align="right",
            ),
        ),
        ui.card_body(
            ui.output_text("selected_view"),
        ),
        full_screen=True,
    )
)
```

#### Toolbar Select Configuration (`ui.toolbar_input_select`)

A compact select input designed for constrained spaces:
- **`id`**: Unique string identifier (accessed in server via `input.<id>()`).
- **`label`**: The select label text. Always provide a meaningful label (even when using `show_label=False`) because it is used for screen readers and tooltips, ensuring your app is accessible.
- **`choices`**: A list of strings, a dictionary mapping values to labels, or a nested dictionary for grouped choices.
- **`icon`**: An optional icon (`faicons.icon_svg(...)`) displayed alongside the select.
- **`show_label`**: Boolean (default `False`). If `False`, the text label is hidden and instead appears as a tooltip on hover. If `True`, the label text is visible alongside the icon.
- **`tooltip`**: Optional custom tooltip text. If omitted and `show_label=False`, the `label` text is automatically used for the tooltip.
- **`selected`**: The initially selected value (defaults to first choice).

#### Toolbar Button Configuration (`ui.toolbar_input_button`)

A compact button designed for toolbars:
- **`id`**: Unique identifier. Behaves like an action button.
- **`label`**: Button label.
- **`icon`**: Optional icon (`icon_svg(...)`).
- **`show_label`**: Boolean. If an icon is provided, `show_label` defaults to `False` and the label text is shown as a tooltip instead.
- **`tooltip`**: Optional custom tooltip text.

#### Structural Elements

- **`ui.toolbar_divider()`**: A thin vertical rule for visually grouping toolbar elements.
- **`ui.toolbar_spacer()`**: An invisible spacer to push items to opposite sides of the toolbar.

#### Server-Side Updates

Inside reactive effects, use the update helpers to dynamically change toolbar inputs:
```python
ui.update_toolbar_input_select(
    "view_mode",
    choices=["Table", "Chart", "Map", "Grid"],
    selected="Chart",
    label="View Mode (Updated)",
    show_label=True,
)

ui.update_toolbar_input_button(
    "export_btn",
    label="Exporting...",
    disabled=True,
)
```

#### Toolbar Decision Rules

- **Sidebar vs Toolbar**: If a control changes the entire dashboard layout or filters the main dataset across cards, put it in the sidebar. If a control changes one card's encoding, sorting, aggregation, annotation, or display mode, put it in that card's toolbar.
- **Popover vs Toolbar**: Use `ui.toolbar()` when a card has multiple inputs/buttons that need custom spacing and grouping. Use `ui.popover()` or `ui.tooltip()` directly inside `ui.card_header()` for single settings icons or simple info popups without toolbars.

## Value Boxes

Use `ui.value_box()` for KPIs and headline metrics.

**Core API:**

```python
ui.layout_column_wrap(
    ui.value_box(
        "Total Users",
        ui.output_text("kpi_users"),
        ui.p(
            ui.tags.span("↑ 4.2%", class_="text-success fw-bold"),
            " vs last month",
            class_="fs-6 text-muted mb-0",
        ),
        showcase=icon_svg("users"),
        theme="primary",
    ),
    ui.value_box(
        "Average Order",
        ui.output_text("kpi_order"),
        ui.p(
            ui.tags.span("↑ 0.8%", class_="text-success fw-bold"),
            " vs target",
            class_="fs-6 text-muted mb-0",
        ),
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
    with ui.value_box(
        showcase=icon_svg("users"),
        theme="primary",
    ):
        "Total Users"
        f"{len(df):,}"
        ui.p(
            ui.tags.span("↑ 12.4%", class_="text-success fw-bold"),
            " vs last month",
            class_="fs-6 text-muted mb-0",
        )
```

Guidelines:

- Keep the row to 3 or 4 boxes.
- Prefer `ui.layout_column_wrap(..., width="240px", fill=False)` so KPI cards wrap before becoming cramped.
- Use default bslib theme colors (`theme="primary"`, `"success"`, `"danger"`, `"info"`, etc.) for value boxes.
- Use icons that reinforce the metric; do not use emojis or generic/unrelated icons.
- Format the displayed value instead of passing a raw float or integer.
- **Mandatory Metric Context & Trends**: Headline metrics must never stand alone. Always provide a clear comparison trend or period label styled with high-contrast Bootstrap tags.

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

### Interactive Sparklines & Showcase Layouts

Embedding a line chart or sparkline is highly effective for visualising trend data directly within a KPI card. Use `showcase_layout="bottom"` to position the widget across the full width of the card's bottom, and `showcase_layout="top right"` for smaller icons.

**Core API:**

```python
ui.value_box(
    "Total Sales in Q2",
    "$2.45M",
    showcase=sw.output_widget("sparkline"),
    showcase_layout="bottom",
)

@sw.render_widget
def sparkline():
    economics = pd.read_csv(app_dir / "economics.csv")
    fig = px.line(economics, x="date", y="psavert")
    fig.update_traces(
        line_color=BRAND_COLORS["primary"],
        line_width=1.5,
        fill="tozeroy",
        fillcolor="rgba(13,110,253,0.15)",
        hoverinfo="y",
    )
    fig.update_xaxes(visible=False, showgrid=False)
    fig.update_yaxes(visible=False, showgrid=False)
    fig.update_layout(
        height=100,
        hovermode="x",
        margin=dict(t=0, r=0, l=0, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
```

**Express API:**

```python
with ui.value_box(showcase=sw.output_widget("sparkline"), showcase_layout="bottom"):
    "Total Sales in Q2"
    "$2.45M"

    with ui.hold():
        @sw.render_widget
        def sparkline():
            economics = pd.read_csv(app_dir / "economics.csv")
            fig = px.line(economics, x="date", y="psavert")
            fig.update_traces(
                line_color=BRAND_COLORS["primary"],
                line_width=1.5,
                fill="tozeroy",
                fillcolor="rgba(13,110,253,0.15)",
                hoverinfo="y",
            )
            fig.update_xaxes(visible=False, showgrid=False)
            fig.update_yaxes(visible=False, showgrid=False)
            fig.update_layout(
                height=100,
                hovermode="x",
                margin=dict(t=0, r=0, l=0, b=0),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            return fig
```

#### Sparkline Styling Guidelines:
- **Hide gridlines and axes**: Always set `visible=False` and `showgrid=False` on both X and Y axes.
- **Transparent background**: Set `plot_bgcolor="rgba(0,0,0,0)"` and `paper_bgcolor="rgba(0,0,0,0)"` so the plot inherits the card's theme color.
- **Remove margins**: Pass `margin=dict(t=0, r=0, l=0, b=0)` so the chart extends edge-to-edge.
- **Accent line and fill**: Color the line with your brand sequence color and fill the area underneath with a low opacity alpha value (e.g. `rgba(..., 0.15)`).
- **Required CSS for ipywidgets / Plotly scaling**: Because ipywidget outputs (like `shinywidgets.output_widget`) nested in value boxes do not automatically expand to fill their parents, you must include CSS styling to force the widget elements to stretch and to hide the Plotly modebar:

  ```css
  .bslib-value-box .plotly .modebar-container {
    display: none;
  }
  .shiny-ipywidget-output {
    display: flex;
    flex: 1 1 auto !important;
    width: 100%;
  }
  .shiny-ipywidget-output > * {
    display: flex;
    flex: 1 1 auto;
    width: 100%;
  }
  .shiny-ipywidget-output > * > * {
    display: flex;
    flex: 1 1 auto;
    width: 100%;
  }
  .shiny-ipywidget-output > * > * > * {
    display: flex;
    flex: 1 1 auto;
    width: 100%;
  }
  ```

  Include this CSS in the page using `ui.tags.style(...)` or within the application's style sheet to ensure the sparkline stretches to fill the bottom of the value box showcase container.




## Data Tables vs. Data Grids (`ui.output_data_frame`)

Shiny provides two native renderers for tabular data, both bound to `ui.output_data_frame("id")` in the UI:

| Feature | `render.DataTable` | `render.DataGrid` |
| --- | --- | --- |
| **Visual Style** | Figure-like view, minimal grid lines, clean margins. | Spreadsheet-like view, full grid lines separating cells. |
| **Primary Use Case** | Executive summaries, KPI breakouts, leaderboards. | Large, dense datasets requiring clear cell borders and sorting. |
| **Row Density** | Best for shorter datasets (typically < 25 rows). | Best for larger datasets (hundreds of rows, virtualized scrolling). |

### Decision Rules:
- **Choose `render.DataTable`** when presenting a polished summary card (e.g., top 10 products, regional sales). It keeps cognitive load low by minimizing borders and grids.
- **Choose `render.DataGrid`** when showing the detailed dataset at the bottom of the page, where users benefit from spreadsheet-style borders, column-by-column filtering (`filters=True`), or editing (`editable=True`).

### Data Table Example (Polished Summary Table)

```python
from shiny import render, ui

# In UI: ui.output_data_frame("revenue_summary")

@render.data_frame
def revenue_summary():
    summary = (
        filtered_data()
        .groupby("region", as_index=False)
        .agg(revenue=("revenue", "sum"), orders=("order_id", "nunique"))
        .sort_values("revenue", ascending=False)
    )
    
    summary_df = summary.copy()
    summary_df["revenue"] = summary_df["revenue"].map(lambda v: f"${v:,.0f}")
    summary_df["orders"] = summary_df["orders"].map(lambda v: f"{int(v):,}")
    
    summary_df = summary_df.rename(columns={
        "region": "Region",
        "revenue": "Revenue",
        "orders": "Orders",
    })
    
    return render.DataTable(
        summary_df,
        width="100%",
        height="350px",
        filters=False,
        styles=[
            # Center the cell text (using Bootstrap utility class)
            {"class": "text-center"},
            # Bold the first column (Region)
            {"cols": [0], "style": {"font-weight": "bold"}},
            # Highlight the top row (index 0) with a light gray background
            {"rows": [0], "style": {"background-color": "#f8f9fa"}},
        ]
    )
```

### Data Grid Example (Dense Drill-Down Table)

```python
from shiny import render, ui

# In UI: ui.output_data_frame("detail_grid")

@render.data_frame
def detail_grid():
    detail_df = filtered_data()[["id", "name", "price", "rating", "status"]].copy()
    
    # Format numeric columns
    detail_df["price"] = detail_df["price"].map(lambda v: f"${v:,.2f}")
    detail_df["rating"] = detail_df["rating"].map(lambda v: f"{v:.1f}")
    
    detail_df = detail_df.rename(columns={
        "id": "ID",
        "name": "Name",
        "price": "Price",
        "rating": "Rating",
        "status": "Status",
    })
    
    return render.DataGrid(
        detail_df,
        width="100%",
        height="450px",
        filters=True,  # Enable column filters for search
        editable=False,
    )
```

Guidelines:

- **Format Numbers First**: Always format numbers (currencies, percentages, counts) in the pandas DataFrame before passing it to the renderer.
- **Rename Columns**: Use human-readable column headers via `.rename(columns=...)`.
- **Set Explicit Height**: Always set a reasonable height (e.g., `height="350px"`) and set `width="100%"` to prevent the table from collapsing or layout shift.
- **Use Styles Natively**: Use the `styles` parameter in `render.DataTable` (or `render.DataGrid`) to apply CSS classes or styles to specific rows and columns. Specify a list of dictionaries with `"class"` (CSS class name string) or `"style"` (dict of CSS property-value pairs), and optionally restrict scope using `"rows"` and/or `"cols"` lists containing 0-based column/row indices.

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

## Table Improvements & Cognitive Load Reduction

To prevent tables from looking like raw, overwhelming spreadsheets, apply these strict design practices:
* **Subset Columns**: Never display all columns from the raw dataset. Subset your dataframe to show only 4–6 essential attributes (e.g., name, price, rating, neighborhood, and status) so the user is not overwhelmed.
* **Row Hover Highlighting**: Always enable row hover highlighting for readability by injecting simple CSS in your app UI:
  ```python
  ui.tags.style("""
      .rt-tbody tr:hover {
          background-color: #f8f9fa !important;
          transition: background-color 0.15s ease-in-out;
      }
  """)
  ```
* **Virtualization and Sorting**: Always configure `render.DataGrid` with `filters=True` (so users can query columns directly), and ensure it has an explicit height floor (at least `height="420px"`) to prevent the grid from collapsing or showing tiny pagination buttons.

## Best Practices

1. Treat cards as the default dashboard container.
2. Use value boxes for headline metrics, not for long explanations.
3. Keep chart options in card-header popovers when they are secondary.
4. Group busy sidebars with accordions.
5. Give icon-only triggers accessible titles.
6. Avoid card-within-card compositions unless you are intentionally creating a nested layout.
