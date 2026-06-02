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

Maps belong in full-screen cards, need explicit height, and depend on clean numeric coordinates (see [references/styling-and-data.md](styling-and-data.md) for early coordinate normalization).

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

Generated apps must render with the dependencies available in the target environment. Prefer `folium` as the **Tier 1 (Preferred)** choice for standard point maps and geographic visuals to mirror the premium style, legends, and popups of R's standard `leaflet` library. `folium` is fully pre-installed in the sandbox, compiles safely to raw HTML, and completely avoids complex widget/ipywidgets serialization errors. If a dynamic R-like live proxy updates markers on active map canvases without rebuilding the frame, `ipyleaflet` can be used as a **Tier 1 (Alternative)**. If a lightweight, vector-only map is preferred, use Plotly `px.scatter_map` as the **Tier 2 (Fallback)**. For massive datasets (>5,000 points), use `lonboard` (Tier 3).

| Library | Use when | Notes |
| --- | --- | --- |
| `folium` | Standard point maps with popup tables, legends, clustering, and rich HTML customization | **Tier 1 (Preferred).** Built on Leaflet. Fully pre-installed and 100% robust via `ui.HTML(m._repr_html_())`. |
| `ipyleaflet` | Interactive point maps with dynamic backend reactivity (leafletProxy equivalent) | **Tier 1 (Alternative).** Requires active notebook widget sessions. Returns an `anywidget`. |
| `plotly.express` | Lightweight point maps or heatmaps without rich popups/legends | **Tier 2 Fallback.** Dependency-safe. Use `scatter_map` or `density_mapbox` with light style. |
| `lonboard` | Point, line, polygon layers with >5,000 and up to ~1M rows | **Tier 3 (Large Datasets).** GPU-accelerated. Returns an `anywidget`. |
| `pydeck` | deck.gl layers not exposed by lonboard (e.g. custom 3D mesh layers) | **Tier 3 Fallback.** Returns `pydeck.Deck`; render via `output_widget`. |

### Tier 1 (Preferred) — `folium` (Leaflet) with Shiny Integration

To integrate `folium` into Shiny for Python apps, you compile the map into standalone HTML using `m._repr_html_()` and render it within a `@render.ui` decorator as `ui.HTML(...)`. This guarantees that Leaflet's CSS and JS run inside an isolated frame, eliminating all browser-side library collisions.

#### Core Best-Practice Patterns

1. **Defensive Coordinate Cleanup**: Always parse coordinate inputs as numeric and drop rows lacking valid geographic locations.
2. **Dynamic Center Re-computation**: Recompute the map viewport center coordinates dynamically from the filtered dataset so the map automatically centers and frames the visible data points.
3. **Marker Clustering**: Use `folium.plugins.MarkerCluster` to bundle adjacent points cleanly, preventing overplotting and massive visual clutter.
4. **Tailored circle markers**: Use `folium.CircleMarker` with explicit radius, custom border/fill colors, and distinct opacity to create professional and elegant representations.
5. **Rich Multi-row HTML Popup Cards**: Build highly customized HTML/CSS popup panels inside an iframe to show formatted metrics (star rating emojis, bold pricing badges, neighborhood details) on click.
6. **Overlay Floating Map Legend**: Add a floating, modern card legend overlaid on the map canvas using `m.get_root().html.add_child(folium.Element(legend_html))`.

```python
import pandas as pd
from shiny import reactive, render
from shiny.express import input, ui

# UI Layout: Map inside a full-screen card with explicit height
with ui.card(height="540px", full_screen=True):
    ui.card_header("Listings Map")
    ui.output_ui("listings_map")

# Server Logic
@render.ui
def listings_map():
    import folium
    from folium.plugins import MarkerCluster
    
    # 1. Clean coordinate data safely
    df_map = filtered_listings().copy()
    df_map["latitude"] = pd.to_numeric(df_map["latitude"], errors="coerce")
    df_map["longitude"] = pd.to_numeric(df_map["longitude"], errors="coerce")
    df_map = df_map.dropna(subset=["latitude", "longitude"])
    
    if df_map.empty:
        return ui.div(
            "No listings with valid coordinates match the current filters.",
            class_="text-muted d-flex align-items-center justify-content-center",
            style="height: 400px; font-style: italic;"
        )
    
    # 2. Recompute map center dynamically
    center_lat = float(df_map["latitude"].mean())
    center_lon = float(df_map["longitude"].mean())
    
    # 3. Initialize map with CartoDB Positron premium light basemap
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="cartodbpositron",
        control_scale=True,
    )
    
    # 4. Add clustering for optimal performance and clean visual flow
    marker_cluster = MarkerCluster(
        options={
            "maxClusterRadius": 35,
            "disableClusteringAtZoom": 14,
            "showCoverageOnHover": False,
        }
    ).add_to(m)
    
    # 5. Define brand color mapping
    COLOR_MAP = {
        "Entire home/apt": "#dc3545",  # elegant crimson red
        "Private room": "#0d6efd",     # primary blue
        "Shared room": "#198754",      # success green
        "Hotel room": "#6f42c1",       # purple
    }
    
    # 6. Generate custom styled circle markers and rich HTML popups
    for _, row in df_map.iterrows():
        room = row.get("room_type", "Entire home/apt")
        color = COLOR_MAP.get(room, "#6c757d")
        
        price_val = row.get("price")
        price_str = f"${price_val:,.0f}" if pd.notna(price_val) else "N/A"
        
        rating_val = row.get("score_rating")
        rating_str = f"⭐ {rating_val:.2f}" if pd.notna(rating_val) else "⭐ N/A"
        
        # Build premium HTML details card for marker popup
        popup_html = f"""
        <div style="font-family: system-ui, -apple-system, sans-serif; width: 220px; padding: 4px; color: #1f2937;">
            <h5 style="margin: 0 0 8px 0; font-size: 14px; font-weight: 700; color: #111827; 
                       white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{row.get('name', 'Listing')}">
                {row.get('name', 'Airbnb Listing')}
            </h5>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 13px; font-weight: 700; color: #dc3545;">{price_str}<span style="font-weight: 400; font-size: 11px; color: #6b7280;">/night</span></span>
                <span style="font-size: 12px; font-weight: 600; background: #f3f4f6; padding: 2px 6px; border-radius: 4px; color: #374151;">{rating_str}</span>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 11px; color: #4b5563;">
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 4px 0; font-weight: 600;">Type:</td>
                    <td style="padding: 4px 0; text-align: right;">{room}</td>
                </tr>
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 4px 0; font-weight: 600;">Neighborhood:</td>
                    <td style="padding: 4px 0; text-align: right;">{row.get('neighborhood', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; font-weight: 600;">Accommodates:</td>
                    <td style="padding: 4px 0; text-align: right;">👤 {int(row.get('n_accommodates', 1))} guests</td>
                </tr>
            </table>
        </div>
        """
        
        iframe = folium.IFrame(popup_html, width=240, height=140)
        popup = folium.Popup(iframe, max_width=250)
        
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=8,
            popup=popup,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=1.5,
        ).add_to(marker_cluster)
        
    # 7. Inject beautiful floating card legend directly onto map canvas
    legend_html = f"""
     <div style="
         position: fixed; 
         bottom: 20px; left: 20px; width: 145px; height: 115px; 
         background-color: white; border: 2px solid #e5e7eb; border-radius: 8px;
         z-index: 9999; font-size: 11px; font-family: system-ui, -apple-system, sans-serif;
         padding: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
         color: #374151;
         ">
         <b style="font-size: 12px; margin-bottom: 6px; display: block; color: #111827;">Room Type</b>
         <div style="display: flex; align-items: center; margin-bottom: 4px;">
             <i style="background: {COLOR_MAP['Entire home/apt']}; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></i>Entire Home
         </div>
         <div style="display: flex; align-items: center; margin-bottom: 4px;">
             <i style="background: {COLOR_MAP['Private room']}; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></i>Private Room
         </div>
         <div style="display: flex; align-items: center; margin-bottom: 4px;">
             <i style="background: {COLOR_MAP['Shared room']}; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></i>Shared Room
         </div>
         <div style="display: flex; align-items: center;">
             <i style="background: {COLOR_MAP['Hotel room']}; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></i>Hotel Room
         </div>
     </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # 8. Compile and return raw HTML inside sandboxed frame
    return ui.HTML(m._repr_html_())
```

### Tier 1 (Alternative) — `ipyleaflet` (Leaflet Equivalent) with Shiny Integration

To integrate `ipyleaflet` into Shiny for Python apps, you must import the widget packages **inside the local render function or reactive effects**. Top-level imports of `ipyleaflet` trigger widget instantiation at module load time, raising a `RuntimeError: shinywidgets requires that all ipywidgets be constructed within an active Shiny session` error.

#### Core Patterns

1. **Initialization (`@render_widget`)**: Create and return the `ipyleaflet.Map` inside a render function. Set a light tile layer (e.g. Positron) for contrast.
2. **Dynamic Reactivity (`@reactive.effect`)**: To update points, layers, or markers when inputs change (without rebuilding/reloading the map canvas or causing flickering), directly add/remove layers on the active widget instance (equivalent to R's `leafletProxy`).

```python
import pandas as pd
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_widget

with ui.card(height="540px", full_screen=True):
    ui.card_header("Listings Map")
    
    @render_widget
    def listings_map():
        # Inner import prevents import-time active session errors
        from ipyleaflet import Map, basemaps, Marker, AwesomeIcon
        
        # Initialize map (mirroring R Leaflet center and tile styling)
        m = Map(
            center=(df["latitude"].mean(), df["longitude"].mean()),
            zoom=11,
            basemap=basemaps.CartoDB.Positron,
            scroll_wheel_zoom=True
        )
        
        # Draw initial markers so they appear immediately on load
        frame = filtered_listings()
        for _, row in frame.iterrows():
            icon = AwesomeIcon(
                name="home" if row["room_type"] == "Entire home/apt" else "bed",
                marker_color="green" if row["room_type"] == "Entire home/apt" else "blue",
                icon_color="white",
                spin=False
            )
            marker = Marker(
                location=(row["latitude"], row["longitude"]),
                icon=icon,
                draggable=False
            )
            m.add(marker)
        return m

# Reactive effect for dynamic markers update (no map canvas reload/flicker)
@reactive.effect
def _update_map_markers():
    if hasattr(listings_map, "widget"):
        from ipyleaflet import Marker, AwesomeIcon, TileLayer
        
        m = listings_map.widget
        
        # Remove any existing markers/non-tile layers (leafletProxy equivalent)
        for layer in list(m.layers):
            if not isinstance(layer, TileLayer):
                m.remove(layer)
                
        # Filter dataframe based on input
        frame = filtered_listings()
        
        # Draw new markers on the existing map canvas
        for _, row in frame.iterrows():
            # Standard FontAwesome icon customization
            icon = AwesomeIcon(
                name="home" if row["room_type"] == "Entire home/apt" else "bed",
                marker_color="green" if row["room_type"] == "Entire home/apt" else "blue",
                icon_color="white",
                spin=False
            )
            marker = Marker(
                location=(row["latitude"], row["longitude"]),
                icon=icon,
                draggable=False
            )
            m.add(marker)
```

Guidelines:
- Clean coordinates (`latitude`, `longitude`) using `pd.to_numeric(..., errors="coerce")` and drop missing values before mapping.
- Use `AwesomeIcon` with a prefix or name (e.g., FontAwesome glyphs) to make professional markers.
- Always use a light basemap style (e.g., `basemaps.CartoDB.Positron`).

#### 3. ipyleaflet Bidirectional Communication
`ipyleaflet` widgets support bidirectional communication to capture client-side user input (clicks, zoom, bounds changes) and reactively update server-side Python calculations.

```python
from shiny import reactive, render
from shiny.express import input, ui
from shinywidgets import render_widget

# Reactive value to capture map viewport bounds
map_bounds = reactive.Value(None)

@render_widget
def interactive_map():
    from ipyleaflet import Map, basemaps
    m = Map(
        center=(37.7749, -122.4194),
        zoom=12,
        basemap=basemaps.CartoDB.Positron
    )
    
    # Observer for bounds changes to update our reactive.Value
    def handle_bounds_change(change):
        map_bounds.set(change['new'])
        
    m.observe(handle_bounds_change, names='bounds')
    return m

# Reactive calculation dynamically filtered by the visible map viewport
@reactive.calc
def points_in_view():
    bounds = map_bounds()
    if not bounds:
        return df
    # bounds is [[south, west], [north, east]]
    lat_min, lon_min = bounds[0]
    lat_max, lon_max = bounds[1]
    return df[
        (df["latitude"] >= lat_min) & (df["latitude"] <= lat_max) &
        (df["longitude"] >= lon_min) & (df["longitude"] <= lon_max)
    ]
```

#### 4. ipyleaflet Layer Management & Performance (GeoJSON)
To maintain rendering performance and minimize serialization overhead when drawing more than ~100 markers, do not spawn individual `Marker` objects. Instead, load the locations into a single `GeoJSON` component layer.

```python
@render_widget
def geojson_map():
    from ipyleaflet import Map, GeoJSON, basemaps
    m = Map(
        center=(37.7749, -122.4194),
        zoom=12,
        basemap=basemaps.CartoDB.Positron
    )
    
    # Construct a single GeoJSON FeatureCollection dictionary
    features = []
    for _, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["longitude"], row["latitude"]]
            },
            "properties": {
                "name": row["name"],
                "category": row["category"]
            }
        })
        
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Add as a single layer
    geojson_layer = GeoJSON(
        data=geojson_data,
        style={
            "fillColor": "#ff5a5f",
            "color": "#ffffff",
            "weight": 2,
            "radius": 8,
            "fillOpacity": 0.8
        },
        hover_style={"fillColor": "#00a699", "fillOpacity": 1.0}
    )
    m.add(geojson_layer)
    return m
```

#### 5. Custom HTML/SVG Markers and CSS Styling
Style leaflet markers using custom raw HTML/SVG elements with `ipyleaflet.DivIcon`, then apply global visual layout changes using Shiny's `ui.tags.style`.

```python
from shiny.express import ui

# Inject CSS to style custom marker classes with animations
ui.tags.style("""
    .pulse-marker {
        background: #ff5a5f;
        border: 2px solid white;
        border-radius: 50%;
        box-shadow: 0 0 0 0 rgba(255, 90, 95, 0.7);
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 90, 95, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(255, 90, 95, 0); }
        100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 90, 95, 0); }
    }
""")

@render_widget
def custom_style_map():
    from ipyleaflet import Map, Marker, DivIcon, basemaps
    m = Map(
        center=(37.7749, -122.4194),
        zoom=12,
        basemap=basemaps.CartoDB.Positron
    )
    
    for _, row in df.iterrows():
        icon = DivIcon(
            html=f'<div class="pulse-marker" title="{row["name"]}"></div>',
            icon_size=[20, 20],
            icon_anchor=[10, 10]
        )
        marker = Marker(location=(row["latitude"], row["longitude"]), icon=icon)
        m.add(marker)
    return m
```

#### 6. leafmap with MapLibre GL Backend
For vector tile rendering, smooth camera transitions, and extruded 3D buildings, initialize `leafmap.Map` using the MapLibre backend.

```python
@render_widget
def maplibre_map():
    import leafmap.maplibre as leafmap
    
    # Initialize MapLibre GL map with 3D buildings
    m = leafmap.Map(
        center=[-122.4194, 37.7749],
        zoom=11,
        style="positron",
        pitch=45
    )
    m.add_3d_buildings()
    return m
```

### Tier 2 — `lonboard` for Large Datasets

Use `lonboard` when visualizing >5,000 points up to ~1M rows. Keep all widget imports inside the local render/effect functions to prevent active session errors.

Guidelines for `lonboard` formatting and dtype safety:
- Project to GeoDataFrame once; do not repeat the conversion across layers.
- Before `from_geopandas()`, reset the index and convert coordinates to `float64`, popup labels to plain Python/object strings, and scalar popup numbers to numpy numeric dtypes. Do not pass pandas Arrow-backed dtypes, nullable extension dtypes, or `convert_dtypes(dtype_backend="pyarrow")` output into lonboard.
- Keep popup column names short — lonboard renders the dict keys verbatim.
- Always use a Positron / light Carto basemap.
- Handle ArrowDtype conversion errors by converting to float: `astype("float64")`.


### Tier 1 Fallback — Plotly `scatter_map`

This is the default fallback when `lonboard` is not available. It avoids blank maps caused by missing optional widget libraries, works with `output_widget()`, and keeps the chart stack consistent.

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


### Custom Markers Across Map Libraries

When building dashboards, standard circle markers may not convey enough semantic context. Below are the patterns to implement custom icons and markers.

#### 1. `ipyleaflet` Markers (AwesomeIcon & Custom Images)
Use `ipyleaflet.AwesomeIcon` for FontAwesome markers and `ipyleaflet.Icon` for custom images. This is the direct Leaflet equivalent.

```python
# FontAwesome icon custom marker
from ipyleaflet import Marker, AwesomeIcon
icon = AwesomeIcon(
    name="home",
    marker_color="green",
    icon_color="white"
)
marker = Marker(location=(lat, lon), icon=icon)

# Custom URL or sprite image custom marker
from ipyleaflet import Marker, Icon
icon = Icon(
    icon_url="https://leafletjs.com/examples/custom-icons/leaf-green.png",
    icon_size=[19, 47],
    icon_anchor=[9, 47]
)
marker = Marker(location=(lat, lon), icon=icon)
```

#### 2. `lonboard` TextLayer (Emoji/Text Markers)
Use `lonboard.experimental.TextLayer` to display emojis or characters as markers. This is GPU-accelerated and handles thousands of points easily.

```python
@render_widget
def emoji_map():
    from lonboard import Map
    from lonboard.experimental import TextLayer
    
    frame = filtered_listings()
    geo_df = _short_keys(frame).pipe(_to_lonboard_geo)
    
    ROOM_GLYPH = {
        "Entire home/apt": "🏠",
        "Private room":    "🛌",
        "Shared room":     "👥",
        "Hotel room":      "🏨",
    }
    
    # Map glyphs/emojis to a numpy object array
    glyphs = geo_df["type"].map(ROOM_GLYPH).fillna("📍").to_numpy(dtype=object)
    
    layer = TextLayer.from_geopandas(
        geo_df,
        get_text=glyphs,
        get_size=20,
        size_units="pixels",
        get_color=[0, 0, 0],
        pickable=True,
    )
    return Map(layer)
```

#### 3. `pydeck` IconLayer (Raster Sprite Markers)
Use `pydeck.Layer("IconLayer")` when you need custom image URLs or local sprites instead of plain text/emojis.

```python
@render_widget
def pydeck_icon_map():
    import pydeck as pdk
    frame = filtered_listings().copy()
    
    # Configure icon dictionary for pydeck
    icon_config = {
        "url": "https://img.icons8.com/color/48/000000/marker.png",
        "width": 128,
        "height": 128,
        "anchorY": 128,
    }
    
    # Each row must contain the icon configuration dictionary
    frame["icon_data"] = [icon_config] * len(frame)
    
    layer = pdk.Layer(
        "IconLayer",
        data=frame,
        get_position=["longitude", "latitude"],
        get_icon="icon_data",
        get_size=4,
        size_scale=10,
        pickable=True,
    )
    
    view_state = pdk.ViewState(
        latitude=frame["latitude"].mean(),
        longitude=frame["longitude"].mean(),
        zoom=11,
    )
    
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="light",
        tooltip={"text": "{name}"}
    )
```

#### 4. `folium` CustomIcon (HTML / Leaflet Image Markers)
Use `folium.CustomIcon` for simple click-through maps (scale < 1,000 points) where you want custom image files.

```python
@render.ui
def folium_custom_map():
    import folium
    from shiny.express import ui
    
    frame = filtered_listings()
    m = folium.Map(location=[frame["latitude"].mean(), frame["longitude"].mean()], zoom_start=11)
    icon_url = "https://leafletjs.com/examples/custom-icons/leaf-green.png"
    
    for _, row in frame.iterrows():
        icon = folium.CustomIcon(
            icon_url,
            icon_size=(19, 47),
            icon_anchor=(11, 47)
        )
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            icon=icon,
            popup=row["name"]
        ).add_to(m)
        
    return ui.HTML(m._repr_html_())
```

#### 5. Plotly `scatter_map` (Text Mode Emojis)
Use Plotly's `mode="text"` to replace circles with Unicode symbols/emojis.

```python
@render_plotly
def plotly_emoji_map():
    import plotly.express as px
    frame = filtered_listings().copy()
    
    fig = px.scatter_map(
        frame,
        lat="latitude",
        lon="longitude",
        hover_name="name",
        zoom=11,
    )
    fig.update_traces(
        mode="text",
        text=frame["room_type"].map({"Hotel room": "🏨"}).fillna("🏠").to_numpy(),
        textfont=dict(size=18),
    )
    fig.update_layout(
        template="plotly_white",
        map_style="carto-positron",
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig
```

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
- Never set a `line` property (e.g. `line=dict(...)`) inside `marker` when calling `fig.update_traces()` on map objects (`px.scatter_map` or `px.scatter_mapbox`). Geographic markers do not support line properties and will raise a ValueError.
- Sizing Null Safety: Sizing columns with missing (`NaN`) values will crash Plotly maps. Always handle and fill null values in columns used for marker sizing (e.g. `size="price"`) using `.fillna(0)` or dropping those rows to avoid a `'size' property is a number` ValueError.
- For `lonboard`, build color and size arrays as `numpy.uint8` / `numpy.float32` once per render — do not iterate per-row in the render function.
- Push live styling/radius filter changes via `@reactive.effect` updating layer attributes directly instead of re-rendering the whole map.
- If coordinates or geometries change, replace the list of layers on the active widget (e.g. `map.widget.layers = [new_layer]`).
- Never plot more than ~5,000 markers without aggregating to hexes, clusters, or using `lonboard` GPU-accelerated layers.
- If the map shares filters with charts, drive everything from the same `@reactive.calc`.

## Best Practices

1. Use icons sparingly and consistently.
2. Add `a11y="sem"` and a useful `title` for icon-only triggers.
3. Clean latitude and longitude before building map outputs.
4. Put maps in full-screen cards with explicit height.
5. Use maps only when location materially changes the analysis.

