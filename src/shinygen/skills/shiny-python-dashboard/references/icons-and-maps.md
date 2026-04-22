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

Default to `lonboard` for point, hex, and text layers. Reach for the next tier only when `lonboard` cannot express the encoding you need.

| Library | Use when | Notes |
| --- | --- | --- |
| `lonboard` | Point, text, hex, or path layers up to ~1M rows | Tier 1 default. GPU-accelerated, returns an `anywidget`. |
| `pydeck` | You need a deck.gl layer that lonboard does not expose (e.g. `IconLayer` with custom sprites) | Tier 2 fallback. Returns a `pydeck.Deck`; render via `output_widget`. |
| `plotly.express` | Density heatmaps, choropleths, or quick prototypes | Tier 3 fallback. Use `density_mapbox` or `choropleth_mapbox` with a light style. |
| `folium` | Static-feeling tile maps with markers and popups | Use only for simple click-through maps; not great for >1k points. |
| `keplergl` | Heavily exploratory analyst tooling | Rarely the right pick for a polished dashboard. |

### Tier 1 — `lonboard` ScatterplotLayer with popup

```python
import lonboard
import numpy as np
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


@render_widget
def listings_map():
    frame = filtered_listings()
    colors = np.array(
        [ROOM_COLOURS.get(r, [120, 120, 120]) for r in frame["room_type"]],
        dtype=np.uint8,
    )
    layer = ScatterplotLayer.from_geopandas(
        _short_keys(frame).pipe(_to_geo),
        get_fill_color=colors,
        get_radius=40,
        radius_min_pixels=2,
        pickable=True,
    )
    return Map(layer, basemap_style=lonboard.basemap.CartoBasemap.Positron)
```

Guidelines:

- Build the `numpy.uint8` color array once per render and pass it as `get_fill_color`.
- Project to GeoDataFrame once; do not repeat the conversion across layers.
- Keep popup column names short — lonboard renders the dict keys verbatim.
- Use a Positron / light Carto basemap.

### Tier 1b — `lonboard` TextLayer with emoji glyphs

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

### Tier 1c — `lonboard` H3HexagonLayer for density

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

### Tier 2 — `pydeck` IconLayer

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

### Tier 3 — Plotly density fallback

Use only when neither lonboard nor pydeck fit (e.g. quick density heatmap with no extra deps).

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
