---
name: shiny-python-dashboard
description: Build polished Shiny for Python dashboards and analytical apps. Use when creating or refactoring Shiny for Python apps, dashboards, KPI layouts, sidebar or navbar navigation, cards, value boxes, responsive grids, reactive filtering, charts, data tables, or when choosing between Core and Express APIs.
---

# Modern Shiny for Python Dashboards

Build professional Shiny for Python dashboards with Shiny's layout primitives, cards, value boxes, and reactive data flow. Keep this root file small: read it first, then load only the reference files that match the task.

## Progressive loading

Do not treat this file as the full handbook. Use it as the routing layer.

After reading this file, load only the references you need:

| Task surface | Read this file |
| --- | --- |
| Page structure, sidebar vs navbar, responsive grids, fill behavior, branded navbar with per-tab icons | [references/layout-and-navigation.md](references/layout-and-navigation.md) |
| Cards, value boxes, accordions, tooltips, KPI value box with period-over-period delta, summary tables with `great_tables` | [references/components.md](references/components.md) |
| Reactive graph design, `@render.plot`, Plotly brand template, `DataGrid` number formatting, empty-state handling | [references/reactivity-and-rendering.md](references/reactivity-and-rendering.md) |
| Themes and brand palette, CSS spacing safety net, number formatting, data loading, project structure | [references/styling-and-data.md](references/styling-and-data.md) |
| Icons, geographic outputs, map-library picker, lonboard / pydeck / Plotly map tiers | [references/icons-and-maps.md](references/icons-and-maps.md) |
| Choosing between Core and Express or translating from one to the other | [references/core-vs-express.md](references/core-vs-express.md) |

If the task spans multiple surfaces, read multiple references. Example: a multi-tab KPI dashboard with Plotly charts should normally load layout, components, reactivity, and styling.

## Default routing

Use these defaults unless the prompt clearly points elsewhere:

1. If the prompt names 3 or more analytical sections such as Performance, Patient Flow, Staffing, or Outcomes, default to `ui.page_navbar()` and read [references/layout-and-navigation.md](references/layout-and-navigation.md).
2. If the app is one workflow with one shared filter set, default to `ui.page_sidebar()` and read [references/layout-and-navigation.md](references/layout-and-navigation.md).
3. If the app has a prominent map, read [references/icons-and-maps.md](references/icons-and-maps.md) before writing code.
4. If the app has a prominent summary table or leaderboard, read [references/components.md](references/components.md) before writing code.
5. If the user asks for Core vs Express guidance, or is translating an R or old Python app, read [references/core-vs-express.md](references/core-vs-express.md) first.

## Always-apply rules

These rules are global and should be applied on almost every dashboard task.

1. Never use emoji characters as icons. Use `faicons.icon_svg()` or Bootstrap Icons SVG instead.
2. Always pass an explicit light `theme=` to your `ui.page_*()` call. Default bslib styling reads as stock Shiny and caps the dashboard visually. Prefer `shinyswatch.theme.zephyr`, `flatly`, `minty`, `cosmo`, `lumen`, or `yeti`.
3. Do not add `ui.input_dark_mode()` to dashboards. Ship a polished light theme instead.
4. Only call `ui.include_css(app_dir / "styles.css")` if you create `styles.css` in the same change. Missing referenced stylesheets break app startup.
5. For dense dashboards, use `fillable=False`. Reserve `fillable=True` for sparse pages with one or two large fillable panels.
6. Keep KPI rows in `ui.layout_column_wrap(..., width="240px", fill=False)` and limit them to 3 to 4 value boxes per row.
7. Give every chart, map, and table card a title via `ui.card_header(...)` and a readable floor such as `min_height="320px"`.
8. Do not place more than 2 medium or large visualization cards in a row.
9. For multi-section dashboards, use `ui.page_navbar()` with one `ui.nav_panel()` per section, add an icon to each tab, and use a branded title block.
10. Make value boxes carry context, not just a number. Pair the headline metric with a small period-over-period delta such as `down 4.1% vs prior period`.
11. Never use Bootstrap `text-success` or `text-danger` directly for delta text inside dark or gradient value boxes. Use a high-contrast pill or badge treatment instead.
12. For Plotly charts, always use `template="plotly_white"` and an explicit 3 to 4 color palette. Default Plotly rainbow colors instantly look auto-generated.
13. Never put more than one chart inside a single `@render.plot`. Do not stack Matplotlib subplots in one card.
14. Format every displayed number for readability, including `render.DataGrid` outputs. Never show raw 6-decimal floats in UI.
15. Prefer `great_tables.GT(...)` for short summary tables and `render.DataGrid(...)` for long filterable drill-down tables.
16. Default to `lonboard` for maps and use a light basemap. Avoid dark basemaps.
17. Handle missing data explicitly with `dropna()`, `pd.to_numeric(..., errors="coerce")`, and `req()`.
18. Keep imports at module scope except `matplotlib.pyplot`, which should be imported inside `@render.plot`.

## Sensible dashboard defaults

Use this content hierarchy by default:

1. KPI row at the top.
2. Charts and maps in the middle.
3. Detailed table at the bottom.

Use these component defaults unless the prompt conflicts:

1. `full_screen=True` on charts, maps, and tables.
2. `ui.layout_column_wrap()` for uniform KPI cards.
3. `ui.layout_columns()` when proportions matter.
4. One shared filtered dataset per page or section via `@reactive.calc`.
5. One chart per card.

## Quick decisions

Use these shortcuts to stay consistent:

1. Need the fastest path to a production-feeling app: navbar layout, light theme, tab icons, KPI deltas, Plotly white template, one card per chart.
2. Need a geographic view: read [references/icons-and-maps.md](references/icons-and-maps.md) and default to `lonboard`.
3. Need a polished summary table: read [references/components.md](references/components.md) and prefer `great_tables`.
4. Need maintainable server logic: read [references/reactivity-and-rendering.md](references/reactivity-and-rendering.md) and centralize filtering in `@reactive.calc`.
5. Need translation guidance: read [references/core-vs-express.md](references/core-vs-express.md).

## Avoid common failure modes

1. Do not ship the default theme.
2. Do not reference a stylesheet file that does not exist.
3. Do not let KPI rows stretch edge to edge or exceed 4 cards before wrapping.
4. Do not cram 3 or more serious charts into one row.
5. Do not put multiple Matplotlib charts into one render function.
6. Do not leave cards untitled.
7. Do not leave numeric columns unformatted in tables.
8. Do not use a map when geography is incidental to the question.

## Minimal execution order

When implementing a dashboard, follow this order:

1. Choose page structure.
2. Choose theme.
3. Define the shared filtered dataset.
4. Build the KPI row.
5. Add chart and map cards.
6. Add the summary or drill-down table.
7. Add small CSS only if needed.
8. Validate empty states, formatting, and startup safety.

## Reference files

- [references/layout-and-navigation.md](references/layout-and-navigation.md)
- [references/components.md](references/components.md)
- [references/reactivity-and-rendering.md](references/reactivity-and-rendering.md)
- [references/styling-and-data.md](references/styling-and-data.md)
- [references/icons-and-maps.md](references/icons-and-maps.md)
- [references/core-vs-express.md](references/core-vs-express.md)
