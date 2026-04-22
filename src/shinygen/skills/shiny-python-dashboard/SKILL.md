---
name: shiny-python-dashboard
description: Build polished Shiny for Python dashboards and analytical apps. Use when creating or refactoring Shiny for Python apps, dashboards, KPI layouts, sidebar or navbar navigation, cards, value boxes, responsive grids, reactive filtering, charts, data tables, or when choosing between Core and Express APIs.
---

# Modern Shiny for Python Dashboards

Build professional dashboards with Shiny for Python's layout primitives, reactive graph, and card-based composition patterns. This skill is the Python equivalent of a modern bslib dashboard workflow: use `ui.page_sidebar()` or `ui.page_navbar()` for page structure, `ui.layout_columns()` or `ui.layout_column_wrap()` for responsive grids, `ui.card()` and `ui.value_box()` for content containers, and `@reactive.calc` plus render decorators for data flow.

## Critical rules

1. Never use emoji characters as icons. Use `faicons.icon_svg()` or Bootstrap Icons SVG instead.
2. Keep value boxes to 3 to 4 per row and use `ui.layout_column_wrap(..., width="240px", fill=False)` or breakpoint-aware columns so they wrap before the layout gets cramped.
3. Use `fillable=False` for dense dashboards with a KPI row plus multiple chart, map, or table rows. Reserve `fillable=True` for pages with only one or two large fillable panels.
4. Give every chart, map, and table card a readable floor such as `min_height="320px"` so plots do not collapse into shallow strips.
5. Do not place more than 2 medium or large visualization cards in a row. Split dense content into more rows, tabs, or pages instead.
6. Give every card a title with `ui.card_header("Title")`.
7. Prefer `ui.layout_column_wrap()` for uniform cards and `ui.layout_columns()` when you need explicit proportions.
8. Handle missing data explicitly with `dropna()`, `pd.to_numeric(..., errors="coerce")`, and `req()`.
9. Keep imports at module scope except `matplotlib.pyplot`, which should be imported inside `@render.plot` to avoid backend issues.
10. Format all displayed numbers for readability with commas, currency symbols, percentages, or compact abbreviations.
11. Keep the default dashboard hierarchy: value boxes at the top, charts in the middle, and the detailed table below.
12. Use breakpoint-aware `col_widths` so the layout still works on mobile.
13. For multi-section dashboards (e.g. *Performance · Patient Flow · Outcomes*), default to `ui.page_navbar()` with one `ui.nav_panel()` per section. Single-page sidebar layouts work for narrow analytical apps; multi-tab layouts consistently feel more "production-grade" for broad operational dashboards.
14. Make value boxes carry context, not just a number. Pair the headline metric with a small period-over-period delta (`↓ 4.1% vs prior period`) using a secondary line and a coloured trend icon — this is the single biggest visual upgrade over a default dashboard.
15. Only call `ui.include_css(app_dir / "styles.css")` if you actually create the `styles.css` file in the same step. A missing referenced stylesheet raises `FileNotFoundError` at startup and the app will not run.
16. Always pass an explicit `theme=` to your `ui.page_*()` call. Default bslib styling reads as "stock Shiny" and caps the dashboard at a 6/10 visual score. Use a **light** `shinyswatch` theme such as `shinyswatch.theme.flatly`, `minty`, `zephyr`, `cosmo`, `lumen`, or `yeti`, or build a small `ui.Theme(version=5).add_defaults(...)` with your brand color and a neutral surface palette. Stick to light themes — dark themes are hard to get right (low contrast on `value_box`, `great_tables`, and `DataGrid` filter inputs) and consistently look worse than a polished light theme.
17. For multi-tab navbars, give every `ui.nav_panel()` an `icon=icon_svg("...")` and set the page `title=` to a `ui.tags.span(icon_svg("hospital-user"), " App Name", class_="d-flex align-items-center gap-2")` brand block. A branded navbar with per-tab icons is the cheapest way to escape the default-Shiny look.
18. For Plotly charts, always pass `template="plotly_white"` (or `plotly_dark`) and an explicit `color_discrete_sequence=` from a 3–4 hue brand palette. Default Plotly rainbow colors are an instant "auto-generated dashboard" tell. Add a chart subtitle via `fig.update_layout(title=dict(text="Chart name", subtitle=dict(text="What the encoding means")))` whenever the encoding is non-obvious.
19. Never put more than one chart inside a single `@render.plot` (no `plt.subplots(nrows=N>1)`). Stacked Matplotlib subplots inside one card consistently produce title-into-frame collisions in screenshots. Split into one card per chart instead and let `ui.layout_columns` arrange them.
20. Format numbers in `render.DataGrid` outputs the same way you format numbers in value boxes. Never display a raw 6-decimal float in a table — apply `df.assign(col=df["col"].map(lambda v: f"{v:,.1f}"))` or `df.style.format(...)` before passing to `DataGrid`.
21. Do **not** add `ui.input_dark_mode()` to dashboards. Dark mode requires hand-tuning every chart, value_box gradient, `great_tables` cell colour, and `DataGrid` filter input — in practice it produces low-contrast "unreadable on cell" results. Ship a polished light theme instead.
22. For *summary* tables (top-N, league tables, KPI breakdowns) prefer `great_tables.GT(...)` over `render.DataGrid` — render via `@render.ui` returning `ui.HTML(GT(df).as_raw_html())`. `great_tables` produces a typeset, publication-quality table with column groups, spanners, formatted units (`fmt_currency`, `fmt_percent`, `fmt_number`), and bar/colour data cells. Reserve `render.DataGrid` for the long, scrollable, *filterable* drill-down table.
23. For maps, **default to `lonboard`** (deck.gl/WebGL binding with first-class Shiny support, no Mapbox token, light Carto basemap). It produces visibly more attractive output than `plotly.express.density_mapbox` or `folium`, supports per-row colours/sizes natively, and renders millions of points smoothly. Use `lonboard.ScatterplotLayer` (categorical-colour markers), `lonboard.TextLayer` with emoji glyphs (unique per-marker icons without a sprite atlas), or `lonboard.H3HexagonLayer` for 3D aggregation. Reach for `pydeck.IconLayer` only when the design genuinely calls for bitmap PNG markers, Plotly `density_mapbox`/`scatter_mapbox` only as a no-widget fallback, and `folium` only for ≤500-point HTML popups. **Do not use `kepler.gl-jupyter`** — last release was 2 years ago and it has no real Shiny integration. Always pick the **light** basemap variant (`CartoBasemap.Positron`, `carto-positron`, `CartoDB positron`); dark basemaps clash with the rest of the dashboard and bury the data.
24. **Use `ui.toolbar()` (Shiny ≥ 1.6) to put per-card controls inside `ui.card_header()` / `ui.card_footer()`** instead of cramming card-specific filters into the global sidebar. Components: `ui.toolbar(align="left"|"right")`, `ui.toolbar_input_button(id, label, icon=..., tooltip=...)`, `ui.toolbar_input_select(id, label, choices=...)`, `ui.toolbar_divider()`, `ui.toolbar_spacer()`. Also useful as an `info` button inside an input `label=ui.toolbar(...)`, and as the `toolbar=` argument of `ui.input_submit_textarea()` for AI-chat composers. Set `shiny>=1.6` in `requirements.txt` / `pyproject.toml`.
25. **Never use Bootstrap's `text-success` / `text-danger` classes for delta lines inside `ui.value_box()` themed with `theme="primary"` or any `theme="bg-gradient-*"`.** Their default green (#198754) / red (#DC3545) fail WCAG AA contrast on those dark backgrounds and produce "barely readable" delta arrows. **Render the delta as a pill badge** with a dark translucent background, white bold label, and only the up/down arrow tinted in the pastel good/bad accent — pastel-colored *text* alone (e.g. `#86EFAC` / `#FCA5A5`) still fails contrast on the bright amber (`bg-gradient-orange-red`) and green (`bg-gradient-teal-green`) themes even with `text-shadow`. Use this pill style on the wrapper span: `display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:999px; background:rgba(15,23,42,0.55); color:#FFFFFF; font-weight:600; border:1px solid rgba(255,255,255,0.25);` and put the arrow in a nested span with `color:#86EFAC` (good) or `#FCA5A5` (bad). Same rule applies to any badge / pill / annotation rendered on a dark gradient.

## Quick Start

**Single-page dashboard with a shared sidebar:**

```python
from pathlib import Path

import pandas as pd
from faicons import icon_svg
from shiny import App, reactive, render, ui

app_dir = Path(__file__).parent
df = pd.read_csv(app_dir / "data.csv")

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select("metric", "Metric", choices=list(df.columns)),
        open="desktop",
    ),
    ui.layout_column_wrap(
        ui.value_box(
            "Rows",
            ui.output_text("row_count"),
            showcase=icon_svg("database"),
            theme="primary",
        ),
        ui.value_box(
            "Average",
            ui.output_text("avg_value"),
            showcase=icon_svg("chart-line"),
            theme="info",
        ),
        width="240px",
        fill=False,
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Distribution"),
            ui.output_plot("distribution"),
            full_screen=True,
            min_height="320px",
        ),
        ui.card(
            ui.card_header("Summary"),
            ui.output_text_verbatim("summary"),
            full_screen=True,
            min_height="320px",
        ),
        col_widths={"sm": 12, "xl": [6, 6]},
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Preview"),
            ui.output_data_frame("preview"),
            full_screen=True,
            min_height="420px",
        ),
        col_widths=[12],
    ),
    title="Dashboard",
    fillable=False,
)


def server(input, output, session):
    @reactive.calc
    def series():
        return pd.to_numeric(df[input.metric()], errors="coerce").dropna()

    @render.text
    def row_count():
        return f"{len(df):,}"

    @render.text
    def avg_value():
        return f"{series().mean():,.1f}"

    @render.text
    def summary():
        return (
            f"Min: {series().min():,.1f}\n"
            f"Median: {series().median():,.1f}\n"
            f"Max: {series().max():,.1f}"
        )

    @render.plot
    def distribution():
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(series(), bins=20, color="#0d6efd", edgecolor="white")
        ax.set_xlabel(input.metric())
        ax.set_ylabel("Count")
        fig.tight_layout()
        return fig

    @render.data_frame
    def preview():
        return render.DataGrid(df.head(20), filters=True)


app = App(app_ui, server)
```

**Multi-page dashboard with a navbar:**

```python
from shiny import App, ui

overview = ui.layout_columns(
    ui.card(ui.card_header("Summary"), "Overview content", full_screen=True),
    ui.card(ui.card_header("Recent activity"), "More content", full_screen=True),
    col_widths=[6, 6],
)

details = ui.navset_card_underline(
    ui.nav_panel("Plot", ui.output_plot("plot")),
    ui.nav_panel("Table", ui.output_data_frame("table")),
    title="Analysis",
)

app_ui = ui.page_navbar(
    ui.nav_panel("Overview", overview),
    ui.nav_panel("Analysis", details),
    title="Analytics Platform",
    fillable=True,
)
```

## Core Concepts

### Page layouts

- `ui.page_sidebar()` is the default for single-page dashboards with one shared set of controls.
- `ui.page_navbar()` is the default for multi-page apps with distinct sections.
- Use `fillable=False` for dense dashboards so stacked rows of cards stay readable instead of shrinking to fit the viewport.
- In Express, use `ui.page_opts(title=..., fillable=True)` and then declare `with ui.nav_panel(...):` blocks.

See [references/layout-and-navigation.md](references/layout-and-navigation.md) for layout, sidebar, navigation, and responsive grid patterns.

### Grids

- `ui.layout_column_wrap()` is the simplest way to build uniform KPI rows or evenly sized cards.
- `ui.layout_columns()` gives you a 12-column grid with breakpoint-aware `col_widths`.
- Negative column widths create intentional gaps when needed.

See [references/layout-and-navigation.md](references/layout-and-navigation.md) and [references/components.md](references/components.md) for detailed layout guidance.

### Cards

Cards are the primary dashboard container. Use `ui.card_header()` for titles, `ui.card_footer()` for context, and `full_screen=True` for plots, maps, and tables.

See [references/components.md](references/components.md) for card composition, tabbed card patterns, and inline controls.

### Toolbars (Shiny ≥ 1.6)

Use `ui.toolbar()` to embed compact controls inside `ui.card_header()`, `ui.card_footer()`, input labels, or `ui.input_submit_textarea(toolbar=...)`. This is the modern, low-noise way to scope controls to a single card instead of pushing more inputs into the global sidebar.

```python
from faicons import icon_svg
from shiny import ui

ui.card(
    ui.card_header(
        "Listing map",
        ui.toolbar(
            ui.toolbar_input_select(
                id="map_basemap",
                label="Basemap",
                choices=["Positron", "Voyager"],
                selected="Positron",
            ),
            ui.toolbar_divider(),
            ui.toolbar_input_button(
                id="map_legend_info",
                label="Legend",
                icon=icon_svg("circle-info"),
                tooltip="H = entire home · P = private · S = shared · L = lodging",
            ),
            align="right",
        ),
    ),
    output_widget("density_map"),
    full_screen=True,
)
```

Components: `ui.toolbar()` (container with `align="left"|"right"`), `ui.toolbar_input_button()` (small action button with optional `tooltip=`), `ui.toolbar_input_select()` (compact dropdown), `ui.toolbar_divider()` (separator), `ui.toolbar_spacer()` (push items to opposite sides). Each input has a matching `ui.update_toolbar_input_*()`. Read inputs in the server with `input.<id>()` like any other input.

Use toolbars for: per-card filters (date range, basemap, palette toggle), info/help tooltips next to inputs (`label=ui.toolbar(ui.toolbar_input_button(..., icon=icon_svg("circle-info"), tooltip="..."), "Threshold", align="left")`), and message-composer actions inside `ui.input_submit_textarea(toolbar=...)`. Do **not** use them as a substitute for the global sidebar — keep cross-cutting filters there.

### Value boxes

Use `ui.value_box()` for KPIs, summaries, and status indicators. Place them in a non-filling row so they stay compact and scannable.

See [references/components.md](references/components.md) for showcase icons, layouts, and dynamic output patterns.

### Reactivity

The primary reactive primitive is `@reactive.calc`. Chain calculations for derived data, and pair `@reactive.effect` with `@reactive.event` for reset buttons or imperative updates.

See [references/reactivity-and-rendering.md](references/reactivity-and-rendering.md) for reactive graph patterns and guardrails.

### Rendering outputs

- Use `@render.plot` for Matplotlib or Seaborn.
- Use `@render.data_frame` with `render.DataGrid(...)` for tables.
- Use `shinywidgets.output_widget()` plus `@render_plotly` for Plotly outputs.
- Use `@render.ui` for small dynamic UI fragments, including dynamic icons.

See [references/reactivity-and-rendering.md](references/reactivity-and-rendering.md) for output-specific guidance.

### Styling and data

Use a `shared.py` module or top-level data-loading block to keep data access, constants, and app directory logic out of reactive code. Pair this with a small `styles.css` file rather than inline styling everywhere.

See [references/styling-and-data.md](references/styling-and-data.md) for project structure, formatting, and styling guidance.

### Icons and maps

Use `faicons.icon_svg()` for dashboard icons and treat map widgets as full-screen cards with clear loading and empty-state behavior.

See [references/icons-and-maps.md](references/icons-and-maps.md) for icon, accessibility, and map patterns.

## Beautiful tables — great_tables

For any *summary* table on a dashboard (top 10 listings, KPI breakdown by
category, league table), use [great_tables](https://posit-dev.github.io/great-tables/)
instead of `render.DataGrid`. `great_tables` ships a publication-quality typeset
table with formatted units, column spanners, in-cell data bars, and
theme-friendly styling. Render via `@render.ui` returning `ui.HTML(...)`.

```python
from great_tables import GT, loc, style
from shiny import App, render, ui

app_ui = ui.page_fillable(
    ui.card(
        ui.card_header("Top neighbourhoods by revenue"),
        ui.output_ui("top_table"),
        full_screen=True,
        min_height="460px",
    ),
)

def server(input, output, session):
    @render.ui
    def top_table():
        top = (
            df.groupby("neighbourhood", as_index=False)
              .agg(listings=("id", "count"),
                   revenue=("price", "sum"),
                   avg_rating=("rating", "mean"))
              .nlargest(10, "revenue")
        )
        gt = (
            GT(top, rowname_col="neighbourhood")
            .tab_header(title="Top 10 neighbourhoods",
                        subtitle="Ranked by total revenue")
            .fmt_number("listings", decimals=0, use_seps=True)
            .fmt_currency("revenue", currency="USD", decimals=0)
            .fmt_number("avg_rating", decimals=2)
            .data_color(
                columns=["revenue"],
                palette=["#fee5d9", "#a50f15"],
            )
            .cols_label(listings="Listings",
                        revenue="Revenue",
                        avg_rating="Avg rating")
            .tab_options(
                table_font_size="13px",
                heading_title_font_size="16px",
                column_labels_font_weight="600",
                table_background_color="transparent",
            )
        )
        return ui.HTML(gt.as_raw_html())
```

Guidelines:

- Always set `tab_header(title=, subtitle=)` so the card double-titles cleanly.
- Use `fmt_currency` / `fmt_percent` / `fmt_number(decimals=, use_seps=True)` — never show raw floats.
- Use `data_color(columns=[...], palette=[...])` for in-cell heatmaps; pick a palette that matches your brand colours.
- Use `cols_label()` to humanise snake_case column names.
- Set `table_background_color="#ffffff"` (or a very light surface like `"#F8FAFC"`) explicitly. Do **not** use `"transparent"` — if the theme background turns dark or a card uses a deep colour, white text will be unreadable on the light `data_color` cells.
- Always pair `data_color` with explicit text colour: `.tab_style(style=style.text(color="#111827"), locations=loc.body())` so cell text stays dark on light heat-map cells regardless of theme.
- Keep `great_tables` for **summary** tables (≤20 rows). For long, filterable drill-down tables stay with `render.DataGrid(filters=True)`.

## Mind-blowing maps

Default `folium.Map()` with OpenStreetMap tiles looks like a 2014 tutorial. Plotly's mapbox is fine for heatmaps but visibly flat for everything else. **Reach for `lonboard` first** — it's a deck.gl/WebGL binding maintained by Development Seed, has first-class Shiny integration, no Mapbox token, light Carto basemap built in, and renders per-row colours and sizes natively. It is the closest Python gets to Kepler/Mapbox-quality maps in a Shiny app.

### Library picker

| Question | Library | Why |
| --- | --- | --- |
| "Show every record with per-row colour/size, possibly with categorical icons" (1 – 3 M points) | **`lonboard`** (Tier 1, default) | WebGL/deck.gl rendering, NumPy-driven per-point styling, light Carto basemap, official Shiny support |
| "Aggregate to hex bins / arcs / 3D extrusion" | **`lonboard`** (`H3HexagonLayer`, `ArcLayer`, `ColumnLayer`) | Same engine, GPU-accelerated 3D |
| "Each marker needs a real PNG icon (e.g. brand logos)" | **`pydeck`** (`IconLayer` with image atlas) | Only deck.gl binding with bitmap icons |
| "Static heatmap of density" | **`plotly.express.density_mapbox`** with `mapbox_style="carto-positron"` | One-liner, no widget overhead |
| "Tiny ≤500-point map with HTML popups, no widget" | **`folium`** with `tiles="CartoDB positron"` + `MarkerCluster` | Server-rendered HTML, zero JS deps |

**Do not use `kepler.gl-jupyter`.** Its last release was 2 years ago, it has no Shiny integration (only `_repr_html_`/static export), and it requires a Mapbox token for the good styles. Lonboard covers every kepler use case from Python.

### Tier 1 — `lonboard` ScatterplotLayer with per-row colour and size (recommended)

This is the new default. Each marker gets its own colour and radius from the dataframe — no clustering tricks, no per-row Python loops, no Mapbox token.

```python
import numpy as np
import geopandas as gpd
from lonboard import Map, ScatterplotLayer
from lonboard.basemap import CartoBasemap
from shiny import reactive
from shinywidgets import output_widget, render_widget

# Categorical RGB palette (room_type → fill colour). Always include alpha 200+.
ROOM_COLOURS = {
    "Entire home/apt": [15, 118, 110, 220],   # teal-700
    "Private room":    [245, 158, 11, 220],   # amber-500
    "Shared room":     [220, 38, 38, 220],    # red-600
    "Hotel room":      [99, 102, 241, 220],   # indigo-500
}

@render_widget
def listings_map():
    df = filtered()                            # reactive pandas DataFrame
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    fill = np.array(
        [ROOM_COLOURS.get(rt, [100, 116, 139, 200]) for rt in gdf["room_type"]],
        dtype=np.uint8,
    )
    radius = np.clip(np.sqrt(gdf["price"].fillna(0)) * 1.4, 30, 220).astype(np.float32)

    layer = ScatterplotLayer.from_geopandas(
        gdf,
        get_fill_color=fill,
        get_radius=radius,
        radius_units="meters",
        radius_min_pixels=4,
        radius_max_pixels=22,
        stroked=True,
        get_line_color=[255, 255, 255, 220],
        line_width_min_pixels=1,
        pickable=True,
    )
    return Map(
        layers=[layer],
        basemap_style=CartoBasemap.Positron,    # always light
        view_state={"longitude": float(gdf.geometry.x.mean()),
                    "latitude":  float(gdf.geometry.y.mean()),
                    "zoom": 11, "pitch": 0},
        height=540,
    )
```

**Efficient updates** — when only the *data* changes, mutate the layer in place instead of returning a new `Map` (per [the official Shiny + lonboard guidance](https://developmentseed.org/lonboard/latest/ecosystem/shiny/)):

```python
@reactive.effect
def _refresh():
    df = filtered()
    listings_map.widget.layers[0].get_fill_color = np.array(
        [ROOM_COLOURS.get(rt, [100, 116, 139, 200]) for rt in df["room_type"]],
        dtype=np.uint8,
    )
```

### Tier 1b — Unique per-marker icons via `lonboard.TextLayer` (emoji / glyph markers)

For "every category gets its own icon" *without* shipping a PNG sprite atlas, render an emoji per row with `TextLayer`. This gets you intuitive, high-contrast markers (🏠 🏨 🛏️ 🚪) overlaid on the basemap.

```python
import numpy as np, geopandas as gpd
from lonboard import Map
from lonboard.experimental import TextLayer       # TextLayer lives in experimental
from lonboard.basemap import CartoBasemap

ROOM_GLYPH = {
    "Entire home/apt": "🏠",
    "Private room":    "🛏️",
    "Shared room":     "🚪",
    "Hotel room":      "🏨",
}

@render_widget
def icon_map():
    df = filtered()
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    glyphs = np.array([ROOM_GLYPH.get(rt, "📍") for rt in gdf["room_type"]])
    sizes  = np.clip(df["price"].fillna(50) / 6, 14, 32).astype(np.float32)

    layer = TextLayer.from_geopandas(
        gdf,
        get_text=glyphs,
        get_size=sizes,
        size_units="pixels",
        get_color=[17, 24, 39, 240],          # dark slate text
        get_background_color=[255, 255, 255, 220],
        get_border_color=[15, 118, 110, 220],
        get_border_width=1,
        background_padding=[6, 4, 6, 4],
        font_family="Inter, system-ui, sans-serif",
        pickable=True,
    )
    return Map(layers=[layer], basemap_style=CartoBasemap.Positron, height=540)
```

### Tier 1c — `lonboard.H3HexagonLayer` for aggregated density

Use this instead of `pydeck.HexagonLayer` for "where is density highest" with 3D extrusion. It takes a `pyarrow.Table` plus a column of H3 cell IDs:

```python
import h3, numpy as np, pyarrow as pa
from lonboard import Map, H3HexagonLayer
from lonboard.basemap import CartoBasemap
from lonboard.colormap import apply_continuous_cmap
from matplotlib import colormaps

@render_widget
def hex_map():
    df = filtered().copy()
    df["h3"] = [h3.latlng_to_cell(lat, lon, 9)
                for lat, lon in zip(df["latitude"], df["longitude"])]
    agg = df.groupby("h3", as_index=False).agg(
        count=("id", "size"), median_price=("price", "median"))
    norm = (agg["median_price"] - agg["median_price"].min()) / (
            agg["median_price"].max() - agg["median_price"].min() + 1e-9)
    table = pa.table({
        "hex": agg["h3"].to_numpy(),
        "median_price": agg["median_price"].to_numpy(),
        "count": agg["count"].to_numpy(),
    })
    layer = H3HexagonLayer(
        table=table,
        get_hexagon="hex",
        get_fill_color=apply_continuous_cmap(norm.to_numpy(), colormaps["plasma"], alpha=210),
        get_elevation=agg["count"].to_numpy() * 40,
        elevation_scale=1,
        extruded=True,
        pickable=True,
    )
    return Map(layers=[layer], basemap_style=CartoBasemap.Positron, height=540,
               view_state={"latitude": float(df.latitude.mean()),
                           "longitude": float(df.longitude.mean()),
                           "zoom": 10, "pitch": 45, "bearing": 15})
```

### Tier 2 — `pydeck.IconLayer` when you genuinely need image markers

Only reach for this if the design calls for *bitmap* icons (brand logos, custom SVG/PNG sprites). Lonboard has no `IconLayer`, but pydeck does and renders inside `shinywidgets`.

```python
import pydeck as pdk
from shinywidgets import render_widget

ICON = {
    "url": "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png",
    "width": 128, "height": 128, "anchorY": 128,
}

@render_widget
def icon_map():
    df = filtered().assign(icon=[ICON] * len(filtered()))
    layer = pdk.Layer(
        "IconLayer", data=df,
        get_icon="icon", get_position=["longitude", "latitude"],
        get_size=4, size_scale=15, pickable=True,
    )
    return pdk.Deck(
        layers=[layer],
        map_style="light",       # never use "dark" / "satellite" defaults
        initial_view_state=pdk.ViewState(
            latitude=df.latitude.mean(), longitude=df.longitude.mean(),
            zoom=11, pitch=0,
        ),
        tooltip={"text": "{name}\n${price}"},
    )
```

### Tier 3 — Plotly density heatmap (fallback when you don't want a JS widget)

```python
import plotly.express as px
from shinywidgets import render_plotly

@render_plotly
def density_map():
    fig = px.density_mapbox(
        filtered(), lat="latitude", lon="longitude", z="price",
        radius=12, zoom=10,
        mapbox_style="carto-positron",      # always the light basemap
        color_continuous_scale="Plasma",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#111827"),
    )
    return fig
```

### Universal map guidelines

- Default to `lonboard`. Drop to Plotly/folium only when explicitly asked for a static HTML map or for ≤500 markers with HTML popups.
- Always use a **light** basemap (`CartoBasemap.Positron`, `mapbox_style="carto-positron"`, `tiles="CartoDB positron"`, `map_style="light"`). Never `dark_matter`, `carto-darkmatter`, `mapbox/dark-v9`, or `"satellite"`.
- Compute the map centre and zoom from the *filtered* data so the map re-frames as the user filters.
- Map cards: `min_height="480px"` minimum, `"600px"` if it's the hero. Set `height=540` (or similar) on the lonboard `Map` so it fills the card.
- For per-row colour, build a `numpy.uint8` array of `[R, G, B, A]` rows — never use a Python loop inside `get_fill_color`. Same for `get_radius` (use `numpy.float32`).
- Reuse `widget.layers[0]` from a `@reactive.effect` instead of returning a new `Map` on every filter change — see lonboard's [Shiny "efficient updates" pattern](https://developmentseed.org/lonboard/latest/ecosystem/shiny/).
- Never load >5k individual markers without aggregation; switch to `H3HexagonLayer` or `HeatmapLayer`.

### Core and Express APIs

Both APIs are first-class. Pick one style for the app and keep it consistent. Core is explicit and easy to factor; Express is concise and works well for smaller apps.

See [references/core-vs-express.md](references/core-vs-express.md) for side-by-side equivalents and selection guidance.

## Common Workflows

### Building a dashboard

1. Choose `ui.page_sidebar()` for one-page analytics or `ui.page_navbar()` for multiple sections.
2. Load the data once at module scope or in `shared.py`, then compute reusable constants for inputs.
3. Put primary filters in a sidebar with `open="desktop"` so mobile starts collapsed.
4. Add KPI value boxes in a `fill=False` row near the top.
5. Use `fillable=False` for dense dashboards with multiple visualization rows or a large table.
6. Arrange cards with `ui.layout_column_wrap()` or `ui.layout_columns()`, and give every visualization card `min_height="320px"` or larger.
7. Enable `full_screen=True` on visualizations and detailed tables.
8. Build the data pipeline through `@reactive.calc` functions, not mutated globals.
9. Finish with a `render.DataGrid(...)` card and minimal CSS overrides.

### Translating or modernizing an existing app

If you are replacing an older Shiny for Python layout or translating an R bslib design into Python:

1. Replace ad hoc `ui.div()` grid wiring with `ui.page_sidebar()`, `ui.page_navbar()`, `ui.layout_columns()`, or `ui.layout_column_wrap()`.
2. Wrap charts and tables in cards with headers and full-screen support.
3. Convert top-line metrics into `ui.value_box()` components.
4. Move repeated data transformations into `@reactive.calc` or `shared.py`.
5. Replace emoji icons with `faicons.icon_svg()`.
6. Audit charts for explicit sizes, axis labels, and missing-data handling.

## Guidelines

1. Prefer Shiny's page and layout primitives over raw `ui.div()` composition when building dashboards.
2. Keep one API style per app unless you have a compelling reason to mix Core and Express.
3. Use `ui.layout_column_wrap(..., width="240px", fill=False)` for KPI rows so they wrap cleanly before cards become cramped. Pass an explicit `gap="1rem"` only if you observe cards rendering edge-to-edge in your specific theme; the bslib defaults are usually fine.
4. Wrap dashboard outputs in cards and default to `full_screen=True` on charts, maps, and tables.
5. Use `fillable=False` for dense dashboards with more than one row of visualization cards.
6. Give plot, map, and table cards a floor like `min_height="320px"`; larger tables often need `min_height="420px"`.
7. Do not place more than 2 medium or large visualization cards in a row.
8. Use responsive `col_widths` such as `{"sm": 12, "md": [6, 6]}` for mobile-safe layouts.
9. Use named Bootstrap theme colors like `"primary"`, `"success"`, `"info"`, `"warning"`, and `"danger"` for value boxes.
10. Place imports at the top of the file, except `matplotlib.pyplot` inside `@render.plot`.
11. Never display raw numbers when a formatted value is more readable.
12. Guard empty selections and filtered datasets with `req()` before rendering.
13. Never pass duplicate keys when unpacking Plotly dicts; merge overrides with `{**base, "key": value}` instead.
14. Reach for `ui.page_navbar()` whenever the prompt names more than two analytical themes (flow, staffing, outcomes, etc.). Multi-tab layouts are perceived as more polished than a single long-scroll page.
15. In every value box, surface a *delta* alongside the headline number — e.g. `↓ 4.1% vs prior period` or `+12 vs yesterday` — using a small text line and a coloured `arrow-up` / `arrow-down` icon. This is the cheapest visual win available.
16. If you reference an external CSS file with `ui.include_css(...)`, you must also create that file in the same write step. Otherwise drop the include — `ui.include_css` raises if the file is missing.

## Avoid Common Errors

1. Do not omit `fill=False` on KPI rows; otherwise value boxes stretch awkwardly.
2. Do not keep a dense dashboard `fillable=True`; that is the fastest way to end up with squished cards and unreadable charts.
3. Do not place more than 2 medium or large visualization cards in a row.
4. Do not omit `min_height="320px"` on visualization cards when the page contains multiple rows.
5. Do not wrap `ui.navset_card_*()` content in another `ui.card()`; the navset is already the card container.
6. Do not import `matplotlib.pyplot` at module scope in dashboard apps.
7. Do not pass the same key through both `**base_dict` and a keyword override in Plotly layout dictionaries.
8. Do not assume a sidebar on `ui.page_navbar()` should drive every page; use page-specific controls when sections need different filters.
9. Do not leave cards untitled or charts unlabeled.
10. Do not call `ui.include_css(app_dir / "styles.css")` without creating `styles.css` in the same step — the app will fail to start with `FileNotFoundError`.
11. Do not over-correct spacing with `!important` CSS overrides in `styles.css`. Modern bslib + Python Shiny renders cards with sensible default gaps; reach for CSS only when you observe a real defect.
12. Do not ship the bslib default theme. Always pass `theme=shinyswatch.theme.<name>` or a custom `ui.Theme(...)` to your `ui.page_*()` call — the default grey-on-white look caps the dashboard at a 6.
13. Do not stack Matplotlib subplots inside a single `@render.plot`. Use one card per chart and let `ui.layout_columns()` arrange them; stacked subplots collide titles into adjacent frames in screenshots.
14. Do not leave Plotly charts with the default rainbow categorical palette. Always pass `template="plotly_white"` and an explicit `color_discrete_sequence=` of 3–4 brand colors.
15. Do not display raw floating-point values in a `render.DataGrid`. Format every numeric column the same way you format value-box numbers.

## Modern look — copy-pasteable patterns

These four patterns lift a generated dashboard from the bslib-default 6/10 band
into the 7–8 "designed" band. Apply all of them by default unless the prompt
explicitly asks for stock styling.

### 1. Custom theme + brand palette

```python
import shinyswatch
from shiny import ui

# Pick a polished *light* theme. Good defaults: cosmo, flatly, minty, zephyr,
# lumen, sandstone, yeti. Avoid darkly/cyborg/superhero — dark themes
# consistently produce low-contrast value_box and great_tables results.
THEME = shinyswatch.theme.zephyr

# Brand-aligned 4-color sequence reused by every chart.
BRAND_COLORS = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626"]

app_ui = ui.page_navbar(
    # ... nav panels ...
    title=ui.tags.span(
        icon_svg("hospital-user"),
        " ED Operations",
        class_="d-flex align-items-center gap-2 fw-semibold",
    ),
    theme=THEME,
    fillable=False,
)
```

### 2. Branded navbar with per-tab icons

```python
from faicons import icon_svg
from shiny import ui

app_ui = ui.page_navbar(
    ui.nav_panel(
        "Performance",
        icon=icon_svg("gauge-high"),
        # ... content ...
    ),
    ui.nav_panel("Patient flow", icon=icon_svg("people-arrows")),
    ui.nav_panel("Outcomes", icon=icon_svg("clipboard-check")),
    sidebar=ui.sidebar(
        ui.input_select("hospital", "Hospital", choices=hospitals),
        # ... more filters ...
    ),
    title=ui.tags.span(
        icon_svg("hospital"),
        " ED Ops Console",
        class_="d-flex align-items-center gap-2 fw-semibold",
    ),
    theme=shinyswatch.theme.zephyr,
)
```

### 3. KPI value box with period-over-period delta

```python
from faicons import icon_svg
from shiny import ui


def value_box_with_delta(
    label: str,
    value: str,
    *,
    delta: float | None = None,
    delta_unit: str = "%",
    higher_is_better: bool = True,
    icon_name: str = "chart-line",
    theme: str = "primary",
):
    """KPI value box that surfaces a directional delta vs. prior period."""
    if delta is None:
        delta_block = None
    else:
        improving = (delta >= 0) == higher_is_better
        arrow = "arrow-up" if delta >= 0 else "arrow-down"
        # IMPORTANT: do NOT use Bootstrap's `text-success` / `text-danger`
        # classes here, and do NOT use pastel-colored *text* on its own —
        # both fail WCAG AA contrast on the bright amber
        # (`bg-gradient-orange-red`) and green (`bg-gradient-teal-green`)
        # value_box themes. Render a dark translucent **pill badge** with
        # white bold label and tint only the arrow in the pastel accent.
        good, bad = "#86EFAC", "#FCA5A5"  # green-300 / red-300
        accent = good if improving else bad
        pill_style = (
            "display:inline-flex; align-items:center; gap:6px;"
            "padding:3px 10px; border-radius:999px;"
            "background:rgba(15,23,42,0.55);"
            "color:#FFFFFF; font-weight:600;"
            "border:1px solid rgba(255,255,255,0.25);"
        )
        delta_block = ui.tags.span(
            ui.tags.span(icon_svg(arrow),
                         style=f"color:{accent}; display:inline-flex;"),
            ui.tags.span(f"{abs(delta):.1f}{delta_unit} vs prior period"),
            class_="small mt-1",
            style=pill_style,
        )

    return ui.value_box(
        label,
        value,
        delta_block,
        showcase=icon_svg(icon_name),
        theme=theme,
        full_screen=False,
    )
```

Use it like:

```python
ui.layout_column_wrap(
    value_box_with_delta("Door-to-provider", "27 min",
                         delta=-4.1, higher_is_better=False, icon_name="stopwatch"),
    value_box_with_delta("LWBS rate", "1.8%",
                         delta=-0.3, higher_is_better=False, icon_name="user-xmark"),
    value_box_with_delta("Throughput", "184 visits/day",
                         delta=+6.2, icon_name="people-arrows"),
    value_box_with_delta("Patient satisfaction", "4.3 / 5",
                         delta=+0.1, icon_name="face-smile"),
    width="240px",
    fill=False,
)
```

### 4. Plotly defaults that don't scream "auto-generated"

```python
import plotly.express as px

PLOTLY_TEMPLATE = "plotly_white"
PLOTLY_FONT = dict(family="-apple-system, system-ui, sans-serif", size=12, color="#374151")


def styled_bar(df, *, x, y, color=None, title, subtitle):
    fig = px.bar(
        df, x=x, y=y, color=color,
        color_discrete_sequence=BRAND_COLORS,
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(
        title=dict(
            text=title,
            subtitle=dict(text=subtitle, font=dict(size=12, color="#6b7280")),
            font=dict(size=16, color="#111827"),
        ),
        font=PLOTLY_FONT,
        margin=dict(l=40, r=20, t=70, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#e5e7eb"),
    )
    return fig
```

Wrap a single chart per `@render_plotly` and one chart per card. Reuse
`PLOTLY_TEMPLATE`, `PLOTLY_FONT`, and `BRAND_COLORS` across every chart so the
dashboard reads as one design system rather than a collage.

### 5. Format numbers in DataGrid columns

```python
@render.data_frame
def detail_table():
    out = df.copy()
    for col in ["los_hours", "boarding_hours", "satisfaction"]:
        out[col] = out[col].map(lambda v: f"{v:,.1f}")
    out["visits"] = out["visits"].map(lambda v: f"{int(v):,}")
    return render.DataGrid(out, filters=True, height="420px")
```

## Number formatting

Always format numbers for display:

```python
f"{count:,}"            # 12,345
f"${amount:,.2f}"       # $1,234.56
f"{ratio:.1%}"          # 78.3%
f"{value:,.1f}"         # 1,234.6


def fmt_large(number):
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{number:,.0f}"
```

## Reference Files

- [references/layout-and-navigation.md](references/layout-and-navigation.md) — page layouts, grids, nav panels, sidebars, and fill behavior
- [references/components.md](references/components.md) — cards, value boxes, accordions, tooltips, popovers, and inline controls
- [references/reactivity-and-rendering.md](references/reactivity-and-rendering.md) — reactive graph design and output rendering patterns
- [references/styling-and-data.md](references/styling-and-data.md) — project structure, data loading, formatting, styling, and themes
- [references/icons-and-maps.md](references/icons-and-maps.md) — icon rules, accessibility, and map container patterns
- [references/core-vs-express.md](references/core-vs-express.md) — API selection and side-by-side equivalents
