"""EV Charging Station Dashboard – Shiny for Python"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from faicons import icon_svg
from shiny import reactive
from shiny.express import input, output, render, ui
from shinywidgets import output_widget, render_widget

# ---------------------------------------------------------------------------
# Data loading with defensive checks
# ---------------------------------------------------------------------------
DATA_PATH = "ev_charging_stations.csv"

try:
    df_full = pd.read_csv(DATA_PATH)
except Exception:
    df_full = pd.DataFrame()

# Ensure required columns exist; fill missing ones with safe defaults
_REQUIRED_COLS = {
    "station_name": "",
    "latitude": 0.0,
    "longitude": 0.0,
    "neighborhood": "Unknown",
    "network_operator": "Unknown",
    "num_ports": 0,
    "connector_type": "Unknown",
    "status": "Unknown",
    "utilization_pct": 0.0,
    "avg_session_kwh": 0.0,
    "sessions_per_day": 0,
    "avg_session_duration_min": 0,
    "revenue_daily_usd": 0.0,
    "uptime_pct_30day": 0.0,
    "outage_incidents_90day": 0,
    "user_rating": 0.0,
    "ev_parking_only": "No",
    "last_inspection_date": "",
}

for col, default in _REQUIRED_COLS.items():
    if col not in df_full.columns:
        df_full[col] = default

# Coerce numeric columns defensively
_NUMERIC_COLS = [
    "num_ports", "utilization_pct", "avg_session_kwh", "sessions_per_day",
    "avg_session_duration_min", "revenue_daily_usd", "uptime_pct_30day",
    "outage_incidents_90day", "user_rating", "latitude", "longitude",
]
for c in _NUMERIC_COLS:
    df_full[c] = pd.to_numeric(df_full[c], errors="coerce").fillna(0)

# Build filter choices safely
def _safe_unique(series: pd.Series) -> list:
    try:
        return sorted(series.dropna().unique().tolist())
    except Exception:
        return []

NEIGHBORHOODS = _safe_unique(df_full["neighborhood"])
OPERATORS = _safe_unique(df_full["network_operator"])
STATUSES = _safe_unique(df_full["status"])
CONNECTORS = _safe_unique(df_full["connector_type"])

# Color palettes
COLORS = {
    "Tesla Supercharger": "#E31937",
    "ChargePoint": "#2DB84B",
    "EVgo": "#0066FF",
    "Blink": "#FF8C00",
    "Electrify America": "#8B5CF6",
}

STATUS_COLORS = {
    "Online": "#22C55E",
    "Offline": "#EF4444",
    "Degraded": "#F59E0B",
    "Maintenance": "#6366F1",
}

DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e2e8f0"),
    margin=dict(l=30, r=20, t=20, b=40),
)

EMPTY_FIG = go.Figure(
    layout=dict(
        **DARK_LAYOUT,
        height=300,
        annotations=[dict(text="No data matches filters", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#94a3b8"))],
    )
)

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
ui.page_opts(title="EV Charging Station Dashboard", fillable=True)

ui.head_content(
    ui.HTML("""
    <style>
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }
    .bslib-value-box .value-box-title { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.8; }
    .bslib-value-box .value-box-value { font-weight: 700; font-size: 1.5rem; }
    .bslib-card { border: 1px solid rgba(255,255,255,0.06); background: #1e293b !important; color: #e2e8f0 !important; }
    .card-header { background: transparent !important; border-bottom: 1px solid rgba(255,255,255,0.08) !important; }
    .sidebar { background: #1e293b !important; }
    .form-group label, .control-label { color: #cbd5e1 !important; font-size: 0.82rem; }
    select, .form-control { background: #334155 !important; color: #e2e8f0 !important; border-color: #475569 !important; }
    .shiny-output-error { color: #f87171; }
    .btn-outline-light { border-color: #475569; color: #94a3b8; }
    .btn-outline-light:hover { background: #334155; color: #f1f5f9; }
    </style>
    """)
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with ui.sidebar(width=280, open="always"):
    ui.HTML("<h5 style='color:#f1f5f9; margin-bottom: 1rem;'>🔌 Filters</h5>")

    ui.input_selectize("neighborhoods", "Neighborhoods",
                       choices=NEIGHBORHOODS, selected=[], multiple=True)
    ui.input_selectize("operators", "Network Operator",
                       choices=OPERATORS, selected=[], multiple=True)
    ui.input_selectize("statuses", "Status",
                       choices=STATUSES, selected=[], multiple=True)
    ui.input_selectize("connectors", "Connector Type",
                       choices=CONNECTORS, selected=[], multiple=True)
    ui.input_switch("ev_only", "EV Parking Only", value=False)
    ui.input_slider("util_range", "Utilization (%)", min=0, max=100, value=[0, 100], step=1)
    ui.hr()
    ui.input_action_button("reset", "↻ Reset Filters", class_="btn-outline-light btn-sm w-100")

# ---------------------------------------------------------------------------
# Title bar
# ---------------------------------------------------------------------------
ui.panel_title(
    ui.HTML("""
    <div style="padding: 0.5rem 0;">
        <h2 style="color:#f1f5f9; margin:0;">⚡ EV Charging Station Dashboard</h2>
        <p style="color:#94a3b8; margin:0; font-size:0.85rem;">
            Monitor station performance, utilization, and revenue across the Bay Area
        </p>
    </div>
    """)
)

# ---------------------------------------------------------------------------
# Reactive filtered data
# ---------------------------------------------------------------------------
@reactive.calc
def filtered_df() -> pd.DataFrame:
    try:
        d = df_full.copy()
        if d.empty:
            return d
        sel_nb = input.neighborhoods()
        if sel_nb:
            d = d[d["neighborhood"].isin(sel_nb)]
        sel_op = input.operators()
        if sel_op:
            d = d[d["network_operator"].isin(sel_op)]
        sel_st = input.statuses()
        if sel_st:
            d = d[d["status"].isin(sel_st)]
        sel_cn = input.connectors()
        if sel_cn:
            d = d[d["connector_type"].isin(sel_cn)]
        if input.ev_only():
            d = d[d["ev_parking_only"] == "Yes"]
        lo, hi = input.util_range()
        d = d[(d["utilization_pct"] >= lo) & (d["utilization_pct"] <= hi)]
        return d
    except Exception:
        return df_full.copy()


@reactive.effect
@reactive.event(input.reset)
def _reset():
    ui.update_selectize("neighborhoods", selected=[])
    ui.update_selectize("operators", selected=[])
    ui.update_selectize("statuses", selected=[])
    ui.update_selectize("connectors", selected=[])
    ui.update_switch("ev_only", value=False)
    ui.update_slider("util_range", value=[0, 100])


# ---------------------------------------------------------------------------
# Value boxes
# ---------------------------------------------------------------------------
with ui.layout_column_wrap(width=1 / 6, gap="12px", heights_equal="row"):

    with ui.value_box(showcase=icon_svg("charging-station", fill="#60a5fa"),
                      theme="bg-dark text-light", full_screen=False):
        "Total Stations"
        @render.text
        def vb_total():
            try:
                return str(len(filtered_df()))
            except Exception:
                return "0"

    with ui.value_box(showcase=icon_svg("gauge-high", fill="#34d399"),
                      theme="bg-dark text-light", full_screen=False):
        "Avg Utilization"
        @render.text
        def vb_util():
            try:
                d = filtered_df()
                return f"{d['utilization_pct'].mean():.1f}%" if not d.empty else "N/A"
            except Exception:
                return "N/A"

    with ui.value_box(showcase=icon_svg("dollar-sign", fill="#fbbf24"),
                      theme="bg-dark text-light", full_screen=False):
        "Total Daily Revenue"
        @render.text
        def vb_revenue():
            try:
                d = filtered_df()
                return f"${d['revenue_daily_usd'].sum():,.0f}" if not d.empty else "N/A"
            except Exception:
                return "N/A"

    with ui.value_box(showcase=icon_svg("bolt", fill="#a78bfa"),
                      theme="bg-dark text-light", full_screen=False):
        "Total Sessions/Day"
        @render.text
        def vb_sessions():
            try:
                d = filtered_df()
                return f"{int(d['sessions_per_day'].sum()):,}" if not d.empty else "N/A"
            except Exception:
                return "N/A"

    with ui.value_box(showcase=icon_svg("star", fill="#f472b6"),
                      theme="bg-dark text-light", full_screen=False):
        "Avg User Rating"
        @render.text
        def vb_rating():
            try:
                d = filtered_df()
                return f"{d['user_rating'].mean():.2f} ★" if not d.empty else "N/A"
            except Exception:
                return "N/A"

    with ui.value_box(showcase=icon_svg("shield-halved", fill="#22d3ee"),
                      theme="bg-dark text-light", full_screen=False):
        "Avg Uptime"
        @render.text
        def vb_uptime():
            try:
                d = filtered_df()
                return f"{d['uptime_pct_30day'].mean():.1f}%" if not d.empty else "N/A"
            except Exception:
                return "N/A"


# ---------------------------------------------------------------------------
# Charts Row 1
# ---------------------------------------------------------------------------
with ui.layout_columns(col_widths=[6, 6], gap="12px"):

    with ui.card(full_screen=True):
        ui.card_header(ui.HTML('<span style="color:#f1f5f9;">📊 Utilization by Neighborhood</span>'))
        output_widget("chart_util_neighborhood")

        @render_widget
        def chart_util_neighborhood():
            try:
                d = filtered_df()
                if d.empty:
                    return EMPTY_FIG
                grp = (d.groupby("neighborhood")["utilization_pct"]
                       .mean().sort_values(ascending=True).reset_index())
                fig = px.bar(
                    grp, x="utilization_pct", y="neighborhood", orientation="h",
                    color="utilization_pct", color_continuous_scale="RdYlGn",
                    range_color=[0, 100],
                    labels={"utilization_pct": "Avg Utilization %", "neighborhood": "Neighborhood"},
                )
                fig.update_layout(**DARK_LAYOUT, height=400, coloraxis_showscale=False)
                return fig
            except Exception:
                return EMPTY_FIG

    with ui.card(full_screen=True):
        ui.card_header(ui.HTML('<span style="color:#f1f5f9;">💰 Daily Revenue by Network Operator</span>'))
        output_widget("chart_revenue_operator")

        @render_widget
        def chart_revenue_operator():
            try:
                d = filtered_df()
                if d.empty:
                    return EMPTY_FIG
                grp = (d.groupby("network_operator")
                       .agg(total_revenue=("revenue_daily_usd", "sum"),
                            station_count=("station_name", "count"))
                       .sort_values("total_revenue", ascending=False).reset_index())
                colors = [COLORS.get(op, "#94a3b8") for op in grp["network_operator"]]
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=grp["network_operator"], y=grp["total_revenue"],
                    marker_color=colors,
                    text=[f"${v:,.0f}" for v in grp["total_revenue"]],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>",
                ))
                fig.update_layout(
                    **DARK_LAYOUT, xaxis_title="Network Operator",
                    yaxis_title="Total Daily Revenue ($)", height=400,
                )
                return fig
            except Exception:
                return EMPTY_FIG


# ---------------------------------------------------------------------------
# Charts Row 2
# ---------------------------------------------------------------------------
with ui.layout_columns(col_widths=[4, 4, 4], gap="12px"):

    with ui.card(full_screen=True):
        ui.card_header(ui.HTML('<span style="color:#f1f5f9;">🔋 Station Status Distribution</span>'))
        output_widget("chart_status_dist")

        @render_widget
        def chart_status_dist():
            try:
                d = filtered_df()
                if d.empty:
                    return EMPTY_FIG
                grp = d["status"].value_counts().reset_index()
                grp.columns = ["status", "count"]
                colors = [STATUS_COLORS.get(s, "#94a3b8") for s in grp["status"]]
                fig = go.Figure(go.Pie(
                    labels=grp["status"], values=grp["count"],
                    marker=dict(colors=colors), hole=0.5,
                    textinfo="label+percent", textfont=dict(color="white"),
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
                ))
                fig.update_layout(
                    **DARK_LAYOUT, height=380, showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15,
                                xanchor="center", x=0.5),
                )
                return fig
            except Exception:
                return EMPTY_FIG

    with ui.card(full_screen=True):
        ui.card_header(ui.HTML('<span style="color:#f1f5f9;">🔗 Sessions vs Utilization</span>'))
        output_widget("chart_sessions_util")

        @render_widget
        def chart_sessions_util():
            try:
                d = filtered_df()
                if d.empty:
                    return EMPTY_FIG
                fig = px.scatter(
                    d, x="sessions_per_day", y="utilization_pct",
                    size="num_ports", color="network_operator",
                    hover_name="station_name", color_discrete_map=COLORS,
                    labels={
                        "sessions_per_day": "Sessions per Day",
                        "utilization_pct": "Utilization %",
                        "network_operator": "Operator",
                        "num_ports": "Ports",
                    },
                    size_max=30,
                )
                fig.update_layout(
                    **DARK_LAYOUT, height=380,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25,
                                xanchor="center", x=0.5),
                )
                return fig
            except Exception:
                return EMPTY_FIG

    with ui.card(full_screen=True):
        ui.card_header(ui.HTML('<span style="color:#f1f5f9;">🛡️ Uptime vs Outage Incidents</span>'))
        output_widget("chart_uptime_outage")

        @render_widget
        def chart_uptime_outage():
            try:
                d = filtered_df()
                if d.empty:
                    return EMPTY_FIG
                fig = px.scatter(
                    d, x="outage_incidents_90day", y="uptime_pct_30day",
                    size="sessions_per_day", color="user_rating",
                    hover_name="station_name", color_continuous_scale="RdYlGn",
                    range_color=[1, 5],
                    labels={
                        "outage_incidents_90day": "Outage Incidents (90 days)",
                        "uptime_pct_30day": "Uptime % (30 days)",
                        "user_rating": "User Rating",
                        "sessions_per_day": "Sessions/Day",
                    },
                    size_max=30,
                )
                fig.update_layout(**DARK_LAYOUT, height=380)
                return fig
            except Exception:
                return EMPTY_FIG


# ---------------------------------------------------------------------------
# Charts Row 3
# ---------------------------------------------------------------------------
with ui.layout_columns(col_widths=[6, 6], gap="12px"):

    with ui.card(full_screen=True):
        ui.card_header(ui.HTML('<span style="color:#f1f5f9;">🏆 Top Stations by Daily Revenue</span>'))
        output_widget("chart_top_revenue")

        @render_widget
        def chart_top_revenue():
            try:
                d = filtered_df()
                if d.empty:
                    return EMPTY_FIG
                top = (d.nlargest(10, "revenue_daily_usd")[
                    ["station_name", "revenue_daily_usd", "network_operator", "utilization_pct"]
                ].sort_values("revenue_daily_usd"))
                fig = px.bar(
                    top, x="revenue_daily_usd", y="station_name", orientation="h",
                    color="utilization_pct", color_continuous_scale="Viridis",
                    labels={
                        "revenue_daily_usd": "Daily Revenue ($)",
                        "station_name": "Station",
                        "utilization_pct": "Utilization %",
                    },
                    hover_data=["network_operator"],
                )
                fig.update_layout(
                    **DARK_LAYOUT, height=420,
                    coloraxis_showscale=True,
                    coloraxis_colorbar=dict(title="Util %"),
                )
                return fig
            except Exception:
                return EMPTY_FIG

    with ui.card(full_screen=True):
        ui.card_header(ui.HTML('<span style="color:#f1f5f9;">📈 Avg Session Energy by Connector Type</span>'))
        output_widget("chart_energy_connector")

        @render_widget
        def chart_energy_connector():
            try:
                d = filtered_df()
                if d.empty:
                    return EMPTY_FIG
                grp = (d.groupby("connector_type")
                       .agg(avg_kwh=("avg_session_kwh", "mean"),
                            total_sessions=("sessions_per_day", "sum"),
                            avg_duration=("avg_session_duration_min", "mean"))
                       .sort_values("avg_kwh", ascending=False).reset_index())
                bar_colors = ["#38bdf8", "#a78bfa", "#fb923c", "#34d399", "#f472b6", "#facc15"]
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=grp["connector_type"], y=grp["avg_kwh"],
                    marker_color=bar_colors[: len(grp)],
                    text=[f"{v:.1f} kWh" for v in grp["avg_kwh"]],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Avg Energy: %{y:.1f} kWh<extra></extra>",
                ))
                fig.update_layout(
                    **DARK_LAYOUT,
                    xaxis_title="Connector Type",
                    yaxis_title="Avg Session Energy (kWh)",
                    height=420,
                )
                return fig
            except Exception:
                return EMPTY_FIG


# ---------------------------------------------------------------------------
# Data table
# ---------------------------------------------------------------------------
_DISPLAY_COLS = [
    "station_name", "neighborhood", "network_operator", "connector_type",
    "num_ports", "status", "utilization_pct", "sessions_per_day",
    "avg_session_kwh", "revenue_daily_usd", "uptime_pct_30day", "user_rating",
]
_DISPLAY_NAMES = [
    "Station", "Neighborhood", "Operator", "Connector",
    "Ports", "Status", "Util %", "Sessions/Day",
    "Avg kWh", "Revenue ($)", "Uptime %", "Rating",
]

with ui.card(full_screen=True):
    ui.card_header(ui.HTML('<span style="color:#f1f5f9;">📋 Station Details</span>'))

    @render.data_frame
    def station_table():
        try:
            d = filtered_df().copy()
            if d.empty:
                return render.DataTable(
                    pd.DataFrame({"Info": ["No stations match the current filters"]}),
                )
            cols = [c for c in _DISPLAY_COLS if c in d.columns]
            d = d[cols].sort_values("revenue_daily_usd", ascending=False).reset_index(drop=True)
            name_map = dict(zip(_DISPLAY_COLS, _DISPLAY_NAMES))
            d.columns = [name_map.get(c, c) for c in d.columns]
            return render.DataTable(d, filters=True, selection_mode="row")
        except Exception:
            return render.DataTable(
                pd.DataFrame({"Error": ["Unable to render table"]}),
            )

    @render.text
    def selection_info():
        try:
            sel = station_table.cell_selection()
            if sel is None or len(sel.get("rows", [])) == 0:
                return "Select a row above to see station details."
            d = filtered_df().sort_values("revenue_daily_usd", ascending=False).reset_index(drop=True)
            rows = list(sel["rows"])
            if len(rows) == 1 and rows[0] < len(d):
                row = d.iloc[rows[0]]
                return (
                    f"📍 {row.get('station_name', '?')} — {row.get('neighborhood', '?')} | "
                    f"{row.get('num_ports', '?')} ports ({row.get('connector_type', '?')}) | "
                    f"Revenue: ${row.get('revenue_daily_usd', 0):,.2f}/day | "
                    f"Utilization: {row.get('utilization_pct', 0)}% | "
                    f"Rating: {row.get('user_rating', 0)}★"
                )
            return f"📍 {len(rows)} stations selected"
        except Exception:
            return "Select a row above to see station details."
