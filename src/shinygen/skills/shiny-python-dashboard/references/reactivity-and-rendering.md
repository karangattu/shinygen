# Reactivity and Rendering in Shiny for Python

This reference covers the reactive graph and output rendering patterns that make a Shiny for Python dashboard predictable and maintainable.

## Reactive Graph Design

### `@reactive.calc`

Use `@reactive.calc` for filtered data, derived metrics, and reusable intermediate objects.

```python
@reactive.calc
def filtered_data():
    frame = df.copy()
    if input.region():
        frame = frame[frame["region"].isin(input.region())]
    return frame


@reactive.calc
def metric_series():
    return pd.to_numeric(filtered_data()[input.metric()], errors="coerce").dropna()
```

Chain reactive calcs instead of repeating the same filtering logic in every output.

### `req()`

Use `req()` to stop the reactive pipeline when an input or intermediate result is empty.

```python
from shiny import req


@reactive.calc
def selected_players():
    players = req(input.players())
    return careers()[careers()["person_id"].isin(players)]
```

This keeps render functions simple and avoids error-prone empty-state code in every output.

### `@reactive.effect` and `@reactive.event`

Use `@reactive.effect` for imperative updates such as resetting inputs or synchronizing dependent controls. Add `@reactive.event(...)` when the effect should only run in response to a specific trigger.

```python
@reactive.effect
@reactive.event(input.reset)
def _():
    ui.update_slider("amount", value=[10, 90])
    ui.update_checkbox_group("service", selected=["Lunch", "Dinner"])
```

Without `@reactive.event`, the effect will rerun whenever one of its reactive dependencies changes.

### No global mutation

Do not mutate module-level globals inside reactive functions. Compute new values and return them through the reactive graph instead.

## Rendering Patterns

### Matplotlib and Seaborn with `@render.plot`

Import `matplotlib.pyplot` inside the render function.

```python
@render.plot
def histogram():
    import matplotlib.pyplot as plt

    series = req(metric_series())
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(series, bins=20, color=BRAND_COLORS["primary"], edgecolor="white")
    ax.set_xlabel(input.metric())
    ax.set_ylabel("Count")
    apply_brand_style(ax)
    fig.tight_layout()
    return fig
```

Per-category bar chart (the most common pattern that breaks color alignment):

```python
@render.plot
def price_by_neighborhood():
    import matplotlib.pyplot as plt

    agg = filtered_data().groupby("neighborhood")["price"].median().sort_values()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(agg.index, agg.values, color=BRAND_SEQUENCE[:len(agg)], edgecolor="white")
    for i, v in enumerate(agg.values):
        ax.text(v + 2, i, f"${v:,.0f}", va="center", fontsize=9, color="#374151")
    ax.set_xlabel("Median Price ($)")
    apply_brand_style(ax)
    fig.tight_layout()
    return fig
```

Rules:

- Always pass `color=BRAND_COLORS["primary"]` for single-series charts or `color=BRAND_SEQUENCE[:len(categories)]` for per-category charts. Never omit the `color` parameter.
- Call `apply_brand_style(ax)` on every axes after plotting.
- use `figsize=(8, 4)` as a strong default
- label axes
- call `fig.tight_layout()` before returning
- drop missing values before plotting

### Plotly with `shinywidgets`

Use `output_widget()` in Core apps and `@render_plotly` in the server or Express block.
Never return a Plotly figure from `@render.plot` or wire them to
`ui.output_plot()`; Shiny for Python will raise a red render error because
that renderer only knows how to handle Matplotlib or Seaborn outputs.

```python
from shinywidgets import output_widget, render_plotly

app_ui = ui.card(
    ui.card_header("Scatterplot"),
    ui.input_select(
        "color_column",
        "Color by",
        choices={"Meal time": "time", "Day": "day", "Smoker": "smoker"},
        selected="time",
    ),
    output_widget("scatterplot"),
    full_screen=True,
)

COLOR_LABELS = {"time": "Meal time", "day": "Day", "smoker": "Smoker"}


@render_plotly
def scatterplot():

    frame = filtered_data()
    color_column = input.color_column()
    if color_column not in frame.columns:
        color_column = "time"
    return px.scatter(
        frame,
        x="total_bill",
        y="tip",
        color=color_column,
        labels={color_column: COLOR_LABELS[color_column]},
        color_discrete_sequence=BRAND_SEQUENCE,
    )
```

When an input controls a Plotly aesthetic (`color=`, `symbol=`, `facet_col=`, `x=`, `y=`), the input value must be an actual dataframe column name. For named `ui.input_select()` choices, put the display label on the left and the column value on the right, as above; do not invert that mapping.

Avoid duplicate keys when you merge Plotly layout dictionaries:

```python
axis_style = {"gridcolor": "#d0d7de", "showline": False}
fig.update_layout(yaxis={**axis_style, "tickfont": {"size": 11}})
```

Do not write `dict(**axis_style, tickfont=...)` if `axis_style` already contains `tickfont`.

#### Plotly defaults that don't scream auto-generated

Default Plotly rainbow palettes and the `plotly` template are the fastest tells of a generated dashboard. Define a small template + helper once and reuse it.

```python
import plotly.graph_objects as go
import plotly.io as pio

PLOTLY_FONT = dict(family="Inter, system-ui, sans-serif", size=13, color="#1f2937")

PLOTLY_TEMPLATE = go.layout.Template(
    layout=dict(
        font=PLOTLY_FONT,
        colorway=BRAND_SEQUENCE,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(showgrid=False, showline=True, linecolor="#e5e7eb", ticks="outside"),
        yaxis=dict(gridcolor="#eef0f3", zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font=PLOTLY_FONT, bordercolor="#e5e7eb"),
    )
)
pio.templates["brand"] = PLOTLY_TEMPLATE
pio.templates.default = "plotly_white+brand"


def styled_bar(frame, *, x, y, color=None, title=None):
    import plotly.express as px
    fig = px.bar(frame, x=x, y=y, color=color, title=title,
                 color_discrete_sequence=BRAND_SEQUENCE)
    fig.update_traces(marker_line_width=0)
    fig.update_layout(title=dict(x=0, font=dict(size=15, color="#111827")))
    return fig
```

Guidelines:

- **Mandatory color rule**: Pass an explicit color palette via `color_discrete_sequence=BRAND_SEQUENCE` or `color_discrete_sequence=[BRAND_COLORS["primary"]]` on every `px.*` call. This is required even when using the registered brand template, because `px.bar(color="column")` without `color_discrete_sequence` will use Plotly's built-in defaults. Never allow plots to fall back to default Plotly colors.
- Always start from `template="plotly_white"` (or the registered `"brand"` template).
- **Output ID Uniqueness**: Every output element (`ui.output_text`, `ui.output_ui`, `output_widget`, `ui.output_data_frame`) must have a **globally unique ID** across the entire app. If you reuse a layout helper (like a metric row) in multiple tabs, you must pass a unique prefix to it (e.g. `kpi_row(prefix="overview")`) and prepend it to the output IDs (e.g. `ui.output_text(f"{prefix}_value")`) so that the same ID is never defined twice.
- **Chart Choice by Purpose**:
  * **Trends over time**: Use thin line charts or continuous area charts.
  * **Category comparisons**: Use standard horizontal bar charts or vertical column charts.
  * **Parts-of-a-whole**: Use donut charts or stacked bars, but limit them to fewer than 5–8 categories.
- **Null / NaN Serialization Safety**: Shiny for Python widgets (e.g. `@render_plotly`) serialize figure data to JSON. If any column passed to Plotly functions (like `px.scatter`, `px.bar`, `px.histogram`) for styling (`color=`, `size=`), hover details (`hover_name=`, `hover_data=`), or axes contains missing (`NaN`/`NaT`) values, the serializer will crash with `ValueError: Out of range float values are not JSON compliant: nan`. Always clean and fill null values in all plotted columns (using `.fillna(0)` or `.fillna("Unknown")`) or drop those rows before building the plot.
- Strip chart junk: hide the top/right spines, drop the y-axis line, soften gridlines.
- Place the legend horizontally above the plot. If the legend is redundant (e.g., when the categories are already clearly labeled on the axis or bars, or there is only a single series), completely hide it using `showlegend=False` in `update_layout`.
- Set `margin` explicitly so titles do not collide with the card header.
- **Categorical Simplification (<5% Rule)**: For bar, column, or pie charts (e.g., Property Types, Connector Types), always combine sparse categories representing **less than 5% of the total dataset** into a single `"Other"` bucket up front. This prevents unreadable, crammed labels:
  ```python
  pcts = df["property_type"].value_counts(normalize=True)
  df["property_type_grouped"] = df["property_type"].apply(
      lambda x: x if pcts.get(x, 0) >= 0.05 else "Other"
  )
  ```
- **Direct Data Labels**: Display raw metrics directly next to or on top of chart bars or columns rather than forcing users to trace grids or hover. Set `texttemplate` and `textposition`:
  ```python
  fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside")
  ```
- **Histogram Widths & Overlays**: Prevent thin, unreadable histogram bars. Define a generous, explicit bin spacing, add solid white borders (`line=dict(color="white", width=1)`), use the brand primary color, and add a marginal box-plot overlay to provide a rich distribution breakdown:
  ```python
  fig = px.histogram(df, x="price", nbins=25, marginal="box", color_discrete_sequence=[BRAND_COLORS["primary"]])
  fig.update_traces(marker=dict(line=dict(color="white", width=1.5)))
  ```
- **Scatter Plot Legibility & Tooltips**: Ensure scatter plots are easy to interpret. Use `BRAND_SEQUENCE` for categorizing series, increase marker dots to an explicit readable scale (`size=8` or `size=9`), add soft opacity to handle overlaps, add white borders, completely disable trendlines unless statistically significant, and build highly informative hover cards using `hover_name` and `hover_data`:
  ```python
  fig = px.scatter(
      df, x="price", y="rating",
      color="room_type",
      color_discrete_sequence=BRAND_SEQUENCE,
      hover_name="listing_name",
      hover_data={"neighborhood": True, "price": ":$,.0f", "rating": ":.2f"}
  )
  fig.update_traces(marker=dict(size=9, opacity=0.75, line=dict(color="white", width=1)))
  ```
- **Sorted & Labeled Category Charts**: Always sort categorical comparison bars in descending or ascending order of values. Place the data label at the end of the bars so differences are immediately clear.

### Tables with `@render.data_frame`

Use `render.DataGrid` for dense, detailed tables that require grid lines, vertical scrolling, or column-based filtering, and `render.DataTable` for presentation-quality summary cards. Both are bound to `ui.output_data_frame()` in the UI.

```python
@render.data_frame
def listings_table():
    # Use DataGrid for detailed lists
    return render.DataGrid(filtered_data(), filters=True, height="450px")
```

Treat the data table or grid as the detailed layer beneath charts and KPIs.

#### Format numbers in `DataGrid` columns

Never surface raw 6-decimal floats in a `DataGrid`. Format the dataframe before handing it to `render.DataGrid`.

```python
@render.data_frame
def listings_table():
    frame = filtered_listings().copy()
    frame["price"]   = frame["price"].map(lambda v: f"${v:,.0f}")
    frame["rating"]  = frame["rating"].map(lambda v: f"{v:.2f}")
    frame["share"]   = frame["share"].map(lambda v: f"{v:.1%}")
    frame["reviews"] = frame["reviews"].map(lambda v: f"{int(v):,}")
    frame = frame.rename(columns={
        "price":   "Price",
        "rating":  "Rating",
        "share":   "Share",
        "reviews": "Reviews",
    })
    return render.DataGrid(frame, filters=True, summary=False, height="420px")
```

Guidelines:

- Format currency, percent, and integer columns up front with f-strings or `fmt_*` helpers from `shared.py`.
- Rename columns to human-readable labels just before rendering.
- Pass `height="420px"` (or larger) so the grid does not collapse inside a card.
- Use `filters=True` for drill-down tables; turn it off for short summary tables (and consider `render.DataTable` instead — see [components.md](components.md)).

### Dynamic UI with `@render.ui`

Use `@render.ui` for small dynamic fragments such as icons, badges, or conditional helper text.

```python
@render.ui
def growth_note():
    if get_change() >= 0:
        return ui.span("Up vs prior period", class_="text-success")
    return ui.span("Down vs prior period", class_="text-danger")
```

Do not build major page sections with `@render.ui` if a regular static layout plus reactive outputs would be simpler.

## Core and Express Equivalents

Core API keeps outputs explicit in the UI tree:

```python
ui.card(ui.card_header("Data"), ui.output_data_frame("table"), full_screen=True)


@render.data_frame
def table():
    return render.DataGrid(filtered_data())
```

Express colocates the UI block and renderer:

```python
with ui.card(full_screen=True):
    ui.card_header("Data")

    @render.data_frame
    def table():
        return render.DataGrid(filtered_data())
```

Both are valid. Choose the style that fits the codebase and keep it consistent.

## Common Patterns

### Reset buttons

Use `@reactive.effect` with `@reactive.event` and the appropriate `ui.update_*()` helpers.

### Cascading inputs

Use a plain `@reactive.effect` when one input's choices depend on the current filtered data.

```python
@reactive.effect
def _():
    choices = dict(zip(filtered_data()["id"], filtered_data()["label"]))
    ui.update_selectize("item", choices=choices)
```

### Derived KPI values

Create one calc per reusable business metric instead of recalculating inside each value box renderer.

## Common Errors

1. Repeating filtering logic in every render function instead of centralizing it in `@reactive.calc`.
2. Forgetting `req()` before indexing into empty selections.
3. Importing `matplotlib.pyplot` at module scope.
4. Building large layouts with `@render.ui` instead of static UI plus small reactive outputs.
5. Duplicating Plotly layout keys during dict unpacking.
