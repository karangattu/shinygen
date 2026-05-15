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
| Cards, value boxes, accordions, toolbars, tooltips, KPI value box with period-over-period delta, summary tables with `great_tables` | [references/components.md](references/components.md) |
| Reactive graph design, `@render.plot`, Plotly brand template, `DataGrid` number formatting, empty-state handling | [references/reactivity-and-rendering.md](references/reactivity-and-rendering.md) |
| Themes and brand palette, CSS spacing safety net, number formatting, data loading, project structure | [references/styling-and-data.md](references/styling-and-data.md) |
| Icons, geographic outputs, map-library picker, lonboard / pydeck / Plotly map tiers | [references/icons-and-maps.md](references/icons-and-maps.md) |
| Choosing between Core and Express or translating from one to the other | [references/core-vs-express.md](references/core-vs-express.md) |

If the task spans multiple surfaces, read multiple references. Example: a multi-tab KPI dashboard with Plotly charts should normally load layout, components, reactivity, and styling.

For a professional analytical dashboard, assume the task spans layout, components, reactivity, and styling unless the user asks for a tiny example. Most benchmark failures come from treating these as optional.

## Default routing

Use these defaults unless the prompt clearly points elsewhere:

1. If the prompt names 3 or more analytical sections such as Performance, Patient Flow, Staffing, or Outcomes, default to `ui.page_navbar()` and read [references/layout-and-navigation.md](references/layout-and-navigation.md).
2. If the app is one workflow with one shared filter set, default to `ui.page_sidebar()` and read [references/layout-and-navigation.md](references/layout-and-navigation.md).
3. If the app has a prominent map, read [references/icons-and-maps.md](references/icons-and-maps.md) before writing code.
4. If the app has any chart card, table card, KPI card, local display option, per-card filter, tooltip, popover, or action button, read [references/components.md](references/components.md) before writing code.
5. If the user asks for Core vs Express guidance, or is translating an R or old Python app, read [references/core-vs-express.md](references/core-vs-express.md) first.

## Always-apply rules

These rules are global and should be applied on almost every dashboard task.

1. Never use emoji characters as icons. Use `faicons.icon_svg()` or Bootstrap Icons SVG instead.
2. Always pass an explicit light `theme=` to your `ui.page_*()` call. Default bslib styling reads as stock Shiny and caps the dashboard visually. Prefer `shinyswatch.theme.zephyr`, `flatly`, `minty`, `cosmo`, `lumen`, or `yeti`.
3. Do not add `ui.input_dark_mode()` to dashboards. Ship a polished light theme instead.
4. Only call `ui.include_css(app_dir / "styles.css")` if you create `styles.css` in the same change. Missing referenced stylesheets break app startup.
5. For dense dashboards, use `fillable=False`. Reserve `fillable=True` for sparse pages with one or two large fillable panels.
6. Keep KPI rows in `ui.layout_column_wrap(..., width="240px", fill=False)` and limit them to 3 to 4 value boxes per row.
7. Always pass `gap="1rem"` (or larger) to every `ui.layout_columns()` and `ui.layout_column_wrap()` call. The bslib default in Shiny for Python is a 0 gutter, so adjacent cards visually collide unless you set `gap=`.
8. Render every KPI tile with `ui.value_box(title, value, showcase=..., theme="primary")`. Do NOT hand-roll metric cards from `ui.div(...)` or raw `ui.card(...)` — `value_box()` ships the spacing, typography, and showcase slot the dashboard needs.
9. Give every chart, map, and table card a title via `ui.card_header(...)` and a readable floor such as `min_height="320px"`.
10. Do not place more than 2 medium or large visualization cards in a row.
11. For multi-section dashboards, use `ui.page_navbar()` with one `ui.nav_panel()` per section, add an icon to each tab, and use a branded title block.
12. Make value boxes carry context, not just a number. Pair the headline metric with a small period-over-period delta such as `down 4.1% vs prior period`.
13. Never use Bootstrap `text-success` or `text-danger` directly for delta text inside dark or gradient value boxes. Use a high-contrast pill or badge treatment instead.
14. For Plotly charts, always use `template="plotly_white"` and an explicit 3 to 4 color palette. Default Plotly rainbow colors instantly look auto-generated.
15. Never return a Plotly figure from `@render.plot`. Use `from shinywidgets import output_widget, render_plotly` for Plotly cards in Core apps, or `@render_widget` for other HTML widgets. `@render.plot` is for Matplotlib and Seaborn only and will surface red render errors for Plotly figures.
16. Never put more than one chart inside a single `@render.plot`. Do not stack Matplotlib subplots in one card.
17. Format every displayed number for readability, including `render.DataGrid` outputs. Never show raw 6-decimal floats in UI.
18. Prefer `great_tables.GT(...)` for short summary tables and `render.DataGrid(...)` for long filterable drill-down tables.
19. Default to `lonboard` for maps and use a light basemap. Avoid dark basemaps.
20. Handle missing data explicitly with `dropna()`, `pd.to_numeric(..., errors="coerce")`, and `req()`.
21. Keep imports at module scope except `matplotlib.pyplot`, which should be imported inside `@render.plot`.
22. Use the dataset the user provided. Do not substitute built-in examples such as `tips`, `diamonds`, `iris`, or `mtcars` unless the prompt explicitly asks for them.
23. Add at least one `ui.toolbar()` in every non-trivial dashboard that targets Shiny >= 1.6. Put local controls in card headers or footers: metric selectors, grouping selectors, basemap/palette toggles, display-mode buttons, reset actions, or info buttons. Keep cross-cutting filters in the sidebar.
24. Do not ship red output errors, blank panels, spinner-only panels, or zero/N/A KPI cards as if they are finished. Add empty states and `req()` guards, then verify screenshots.
25. Every chart card should have a working output on initial load using the default filters. If a filter can legitimately remove all data, show a clear empty-state message in the card instead of an exception.

## Sensible dashboard defaults

Use this content hierarchy by default:

1. KPI row at the top.
2. Charts and maps in the middle, with per-card toolbars for local controls.
3. Detailed table at the bottom, ideally with a toolbar for search/reset/export/display controls when relevant.

Use these component defaults unless the prompt conflicts:

1. `full_screen=True` on charts, maps, and tables.
2. `ui.layout_column_wrap()` for uniform KPI cards.
3. `ui.layout_columns()` when proportions matter.
4. One shared filtered dataset per page or section via `@reactive.calc`.
5. One chart per card.
6. `ui.toolbar()` inside card headers for secondary controls instead of growing the sidebar.

## Quick decisions

Use these shortcuts to stay consistent:

1. Need the fastest path to a production-feeling app: navbar layout, light theme, tab icons, KPI deltas, Plotly white template, one card per chart.
2. Need a geographic view: read [references/icons-and-maps.md](references/icons-and-maps.md) and default to `lonboard`.
3. Need a polished summary table: read [references/components.md](references/components.md) and prefer `great_tables`.
4. Need maintainable server logic: read [references/reactivity-and-rendering.md](references/reactivity-and-rendering.md) and centralize filtering in `@reactive.calc`.
5. Need translation guidance: read [references/core-vs-express.md](references/core-vs-express.md).
6. Need local chart/table controls: use `ui.toolbar()` in `ui.card_header()` instead of adding more global sidebar controls.

## Avoid common failure modes

1. Do not ship the default theme.
2. Do not reference a stylesheet file that does not exist.
3. Do not let KPI rows stretch edge to edge or exceed 4 cards before wrapping.
4. Do not cram 3 or more serious charts into one row.
5. Do not put multiple Matplotlib charts into one render function.
6. Do not leave cards untitled.
7. Do not leave numeric columns unformatted in tables.
8. Do not use a map when geography is incidental to the question.
9. Do not ignore the provided CSV or replace it with a package sample dataset.
10. Do not leave a page that appears to render but shows errors, spinners, blank cards, or all-zero KPIs.
11. Do not put every control in the sidebar. Use card toolbars for local display controls so the sidebar stays focused on global filters.

## Minimal execution order

When implementing a dashboard, follow this order:

1. Choose page structure.
2. Choose theme.
3. Define the shared filtered dataset.
4. Build the KPI row.
5. Add chart and map cards with at least one useful toolbar across the dashboard.
6. Add the summary or drill-down table.
7. Add small CSS only if needed.
8. Validate data source, empty states, formatting, startup safety, and screenshots for every tab.

## Final quality gate

Before considering a dashboard done, check these items:

1. The app reads the requested dataset path and no unrelated sample dataset is imported.
2. Every tab/page has at least one meaningful rendered artifact: KPI, chart, map, table, or narrative summary.
3. No card shows a traceback, red render error, permanent spinner, empty gray output, or accidental all-zero/N/A summary.
4. At least one card uses `ui.toolbar()` for a local control or info/action button when Shiny >= 1.6 is available.
5. The initial default filters produce non-empty charts and tables.
6. A browser screenshot of each tab looks like a professional dashboard, not just a technically launched app shell.

## Reference files

- [references/layout-and-navigation.md](references/layout-and-navigation.md)
- [references/components.md](references/components.md)
- [references/reactivity-and-rendering.md](references/reactivity-and-rendering.md)
- [references/styling-and-data.md](references/styling-and-data.md)
- [references/icons-and-maps.md](references/icons-and-maps.md)
- [references/core-vs-express.md](references/core-vs-express.md)
