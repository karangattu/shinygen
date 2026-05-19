# Icons and Maps in Shiny for Python Dashboards

This reference covers two dashboard details that strongly affect quality: icon usage and geographic views. Both should feel intentional, readable, and easy to expand.

## Icons

Use `faicons.icon_svg()` for dashboard icons.

```python
from faicons import icon_svg

icon_svg("chart-line")
icon_svg("users")
icon_svg("dollar-sign")
icon_svg("globe")
```

Guidelines:

- Never use emoji characters as icons.
- Use icons to reinforce a metric or action, not to decorate every label.
- Keep icon choice semantically close to the content.
- Reuse a small icon vocabulary across the app.

### Accessible icon-only triggers

When an icon is the only visible trigger for a tooltip, popover, or action, mark it as semantic and provide a meaningful title.

```python
ui.tooltip(
    icon_svg("circle-info", title="More information", a11y="sem"),
    "Explains how this value is calculated",
)
```

The title should describe the purpose of the trigger, not the icon itself.

### Common dashboard icons

- `"chart-line"` for trends and time series
- `"chart-bar"` for comparisons
- `"users"` or `"user"` for people counts
- `"dollar-sign"` or `"wallet"` for money metrics
- `"percent"` for ratios and conversion
- `"globe"` or `"map"` for geographic views
- `"table"` for tabular drill-downs
- `"filter"` for filter controls

## Maps

The repo already contains Python dashboard examples with geographic outputs, so the guidance here should be concrete: maps belong in full-screen cards, need explicit height, and depend on clean numeric coordinates.

### Clean coordinates first

```python
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
map_data = df.dropna(subset=["latitude", "longitude"])
```

Do not defer coordinate cleanup to the rendering function if the whole dashboard depends on the map.

### Put maps in full-screen cards

```python
ui.card(
    ui.card_header("Market map"),
    output_widget("market_map", height="540px"),
    full_screen=True,
)
```

Guidelines:

- Give the map an explicit height.
- Use `full_screen=True` so users can inspect dense point layers.
- Keep map controls in the sidebar or a small popover, not spread across the page.
- Remove extra padding when the visual should run edge to edge.

### Match the map to the question

Use the map when users need to answer geographic questions such as:

- where listings cluster
- which neighborhoods command higher prices
- how a filtered subset changes by location
- which points deserve drill-down inspection

If the geography is incidental, use a ranked table or bar chart instead.

### Picking a map library

Generated benchmark apps must render with the dependencies available in the target environment. Do not import `lonboard`, `pydeck`, `folium`, or `keplergl` unless that dependency is declared and installed for the app. For ordinary point maps, default to Plotly `px.scatter_map` because it is already used by the dashboard chart stack and does not need an extra map widget package.

| Library | Use when | Notes |
| --- | --- | --- |
| `plotly.express` | Standard dashboard point maps, density maps, choropleths, and dependency-safe generated apps | Tier 1 default. Use `scatter_map`, `density_mapbox`, or `choropleth_mapbox` with a light style. |
| `lonboard` | Point, text, hex, or path layers up to ~1M rows when the dependency is declared | Tier 2 for large/GPU maps. Returns an `anywidget`. |
| `pydeck` | You need a deck.gl layer that lonboard does not expose (e.g. `IconLayer` with custom sprites) and the dependency is declared | Tier 3 fallback. Returns a `pydeck.Deck`; render via `output_widget`. |
| `folium` | Static-feeling tile maps with markers and popups | Use only for simple click-through maps; not great for >1k points. |
| `keplergl` | Heavily exploratory analyst tooling | Rarely the right pick for a polished dashboard. |

### Tier 1 — Plotly `scatter_map`

This is the default for generated Shiny for Python dashboards. It avoids blank maps caused by missing optional widget libraries, works with `output_widget()`, and keeps the chart stack consistent.

```python
import pandas as pd
import plotly.express as px
from shinywidgets import output_widget, render_plotly

ROOM_COLORS = {
    "Entire home/apt": "#0d6efd",
    "Private room": "#198754",
    "Shared room": "#ffc107",
    "Hotel room": "#dc3545",
}

ui.card(
    ui.card_header("Listing locations"),
    output_widget("listings_map", height="540px"),
    full_screen=True,
    min_height="540px",
)

@render_plotly
def listings_map():
    frame = filtered_listings().copy()
    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    frame = frame.dropna(subset=["latitude", "longitude"])
    if frame.empty:
        return empty_fig("No listings with valid coordinates")

    fig = px.scatter_map(
        frame,
        lat="latitude",
        lon="longitude",
        color="room_type",
        color_discrete_map=ROOM_COLORS,
        hover_name="name",
        hover_data={
            "neighborhood": True,
            "price": ":$,.0f",
            "score_rating": ":.2f",
            "latitude": False,
            "longitude": False,
        },
        zoom=10,
        height=540,
    )
    fig.update_layout(
        template="plotly_white",
        map_style="carto-positron",
        map_center={
            "lat": float(frame["latitude"].mean()),
            "lon": float(frame["longitude"].mean()),
        },
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig
```

Guidelines:

- Use `@render_plotly`, not `@render_widget`, for Plotly maps.
- Keep the map output as `output_widget(...)`; Plotly widgets still render through `shinywidgets`.
- Always set `height`, `map_style`, `map_center`, and zero margins.
- Build `hover_data` only from columns that exist in the dataset when the schema is uncertain.

### Tier 2 — `lonboard` ScatterplotLayer with popup

```python
import lonboard
import numpy as np
import geopandas as gpd
import pandas as pd
from lonboard import Map, ScatterplotLayer
from shinywidgets import output_widget, render_widget

ROOM_COLOURS = {
    "Entire home/apt": [13, 110, 253],
    "Private room":    [25, 135, 84],
    "Shared room":     [255, 193, 7],
    "Hotel room":      [220, 53, 69],
}


def _short_keys(frame):
    # Lonboard popups read better with short field names.
    return frame.rename(columns={
        "name": "name", "price": "$", "room_type": "type",
        "number_of_reviews": "rev", "review_scores_rating": "score",
    })[["name", "$", "type", "rev", "score", "latitude", "longitude"]]


def _to_lonboard_geo(frame):
    # Keep lonboard inputs on plain pandas/numpy dtypes. Arrow-backed or
    # nullable extension dtypes can surface as runtime ArrowDtype failures.
    geo = frame.copy().reset_index(drop=True)
    geo["latitude"] = pd.to_numeric(geo["latitude"], errors="coerce").astype("float64")
    geo["longitude"] = pd.to_numeric(geo["longitude"], errors="coerce").astype("float64")
    geo = geo.dropna(subset=["latitude", "longitude"])
    for column in ["name", "type"]:
        geo[column] = geo[column].fillna("").astype(str).astype(object)
    for column in ["$", "rev", "score"]:
        geo[column] = pd.to_numeric(geo[column], errors="coerce").astype("float64")
    return gpd.GeoDataFrame(
        geo,
        geometry=gpd.points_from_xy(geo["longitude"], geo["latitude"]),
        crs="EPSG:4326",
    )


@render_widget
def listings_map():
    frame = filtered_listings()
    colors = np.array(
        [ROOM_COLOURS.get(r, [120, 120, 120]) for r in frame["room_type"]],
        dtype=np.uint8,
    )
    layer = ScatterplotLayer.from_geopandas(
        _short_keys(frame).pipe(_to_lonboard_geo),
        get_fill_color=colors,
        get_radius=40,
        radius_min_pixels=2,
        pickable=True,
    )
    return Map(layer, basemap_style=lonboard.basemap.CartoBasemap.Positron)
```

Use this only when `lonboard` is installed or declared in the generated app dependencies.

Guidelines:

- Build the `numpy.uint8` color array once per render and pass it as `get_fill_color`.
- Project to GeoDataFrame once; do not repeat the conversion across layers.
- Before `from_geopandas()`, reset the index and convert coordinates to `float64`, popup labels to plain Python/object strings, and scalar popup numbers to numpy numeric dtypes. Do not pass pandas Arrow-backed dtypes, nullable extension dtypes, or `convert_dtypes(dtype_backend="pyarrow")` output into lonboard.
- Keep popup column names short — lonboard renders the dict keys verbatim.
- Use a Positron / light Carto basemap.

### Tier 2b — `lonboard` TextLayer with emoji glyphs

Good for category icons that should be readable at any zoom.

```python
from lonboard import TextLayer

ROOM_GLYPH = {
    "Entire home/apt": "\U0001F3E1",  # house
    "Private room":    "\U0001F6CC",  # bed
    "Shared room":     "\U0001F46B",  # people
    "Hotel room":      "\U0001F3E8",  # hotel
}

labels = frame["room_type"].map(ROOM_GLYPH).fillna("\u2022").to_numpy()
text_layer = TextLayer.from_geopandas(
    frame.pipe(_to_geo),
    get_text=labels,
    get_size=18,
    size_units="pixels",
    get_color=[33, 37, 41],
    pickable=True,
)
```

### Tier 2c — `lonboard` H3HexagonLayer for density

```python
import h3
from lonboard import H3HexagonLayer
from lonboard.colormap import apply_continuous_cmap
from matplotlib import colormaps

frame["hex"] = [h3.latlng_to_cell(lat, lng, 8)
                for lat, lng in zip(frame["latitude"], frame["longitude"])]
agg = frame.groupby("hex", as_index=False).size()
normed = (agg["size"] - agg["size"].min()) / max(agg["size"].ptp(), 1)
colors = apply_continuous_cmap(normed.to_numpy(), colormaps["viridis"], alpha=0.85)

hex_layer = H3HexagonLayer(
    get_hexagon=agg["hex"].to_numpy(),
    get_fill_color=colors,
    extruded=False,
    pickable=True,
)
```

### Tier 3 — `pydeck` IconLayer

Use when you need genuine sprite icons that are not glyphs.

```python
import pydeck as pdk

icon_atlas = {
    "home":  {"url": "https://.../home.png",  "width": 128, "height": 128, "anchorY": 128},
    "hotel": {"url": "https://.../hotel.png", "width": 128, "height": 128, "anchorY": 128},
}

frame["icon"] = frame["room_type"].map({
    "Entire home/apt": icon_atlas["home"],
    "Hotel room":      icon_atlas["hotel"],
})

layer = pdk.Layer(
    "IconLayer", data=frame, get_position=["longitude", "latitude"],
    get_icon="icon", get_size=4, size_scale=10, pickable=True,
)
view = pdk.ViewState(latitude=frame["latitude"].mean(),
                     longitude=frame["longitude"].mean(), zoom=11)
deck = pdk.Deck(layers=[layer], initial_view_state=view,
                map_style="light", tooltip={"text": "{name}\n${price}"})
```

Render with `@render_widget` from `shinywidgets`.

### Plotly density fallback

Use this when a point map overplots heavily and you need a quick heatmap without adding dependencies.

```python
import plotly.express as px

fig = px.density_mapbox(
    frame, lat="latitude", lon="longitude", z="price",
    radius=12, zoom=11, mapbox_style="carto-positron",
    center={"lat": frame["latitude"].mean(), "lon": frame["longitude"].mean()},
    color_continuous_scale="Viridis",
)
fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=540)
```

### Universal map guidelines

- Always use a light basemap (Positron / Carto Light). Dark basemaps look gimmicky and reduce contrast on points.
- Recompute the map center from the filtered dataset instead of hard-coding coordinates.
- Give the map card `min_height="420px"` to `"560px"` and `full_screen=True`.
- For Plotly point maps, prefer `px.scatter_map` over deprecated `px.scatter_mapbox` in new code.
- For `lonboard`, build color and size arrays as `numpy.uint8` / `numpy.float32` once per render — do not iterate per-row in the render function.
- Push live filter changes via `@reactive.effect` updating `layer.data` / `layer.get_fill_color` instead of re-rendering the whole `Map` when possible.
- Never plot more than ~5,000 markers without aggregating to hexes or clusters first.
- If the map shares filters with charts, drive everything from the same `@reactive.calc`.

## Best Practices

1. Use icons sparingly and consistently.
2. Add `a11y="sem"` and a useful `title` for icon-only triggers.
3. Clean latitude and longitude before building map outputs.
4. Put maps in full-screen cards with explicit height.
5. Use maps only when location materially changes the analysis.
