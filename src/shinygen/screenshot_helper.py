"""
Screenshot helper — captures a Shiny app across every visible tab / nav-panel.

Usage:
    python screenshot_helper.py [--port PORT] [--output PATH] [--wait SECONDS]

By default writes a numbered series of full-page screenshots into the
output directory:

    screenshot_01_landing.png
    screenshot_02_<tab-slug>.png
    screenshot_03_<tab-slug>.png
    ...

For backwards compatibility the landing capture is also copied to
``--output`` (default ``/home/user/project/screenshot.png``) so older
tooling that expects a single file still works.

Pre-installed inside the Docker sandbox. Used by the agent for visual
self-evaluation of generated Shiny apps.

NOTE: The Shiny-wait + tab-detection logic here mirrors screenshot.py
(host-side). Both use the same viewport and capture strategy. Keep in sync.
"""

import argparse
import os
import re
import shutil
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

# Shared viewport/wait constants (mirrored from config.py for standalone use)
DEFAULT_VIEWPORT = (1920, 1080)
DEFAULT_WAIT = 7.0
SHINY_CONNECT_TIMEOUT = 20000  # ms
SHINY_BUSY_TIMEOUT = 10000  # ms
MAX_TAB_SCREENSHOTS = 8

_TAB_SELECTOR_JS = """
() => {
    const seen = new Set();
    const items = [];
    const candidates = document.querySelectorAll(
        '[data-bs-toggle="tab"],'
        + '[data-bs-toggle="pill"],'
        + '[data-toggle="tab"],'
        + '[data-toggle="pill"],'
        + '[role="tab"],'
        + '.bslib-page-navbar .navbar-nav .nav-link,'
        + '.shiny-tab-input ~ .nav .nav-link'
    );
    candidates.forEach((el, idx) => {
        if (el.classList.contains('active') || el.getAttribute('aria-selected') === 'true') return;
        if (el.classList.contains('dropdown-toggle')) return;
        const key = (el.getAttribute('href') || '')
            + '|' + (el.getAttribute('data-bs-target') || '')
            + '|' + (el.getAttribute('data-value') || '')
            + '|' + (el.textContent || '').trim();
        if (!key || seen.has(key)) return;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return;
        seen.add(key);
        items.push({
            index: idx,
            label: (el.textContent || '').trim().slice(0, 40) || ('tab-' + items.length),
        });
    });
    return items;
}
"""


def _slugify(label: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-").lower()
    return slug[:32] or "tab"


def _wait_for_shiny_render(page: "Page", wait: float = DEFAULT_WAIT) -> None:
    """Wait for Shiny to connect and render outputs.

    Strategy (each step is best-effort, never raises):
      1. Wait for the network to go idle (tiles, fonts, JS bundles).
      2. Wait for Shiny + at least one bound output to exist.
      3. Sleep ``wait`` seconds for deferred async renders.
      4. Wait until ``html.shiny-busy`` is gone.
      5. Wait for leaflet tiles and plotly SVGs to finish drawing.

    This shared logic is used by both the in-sandbox helper and
    the host-side screenshot module.
    """
    # 1. Network idle (tiles, fonts, JS bundles)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    # 2. Shiny connection + bound outputs
    try:
        page.wait_for_function(
            """() => {
                if (typeof Shiny === 'undefined') return false;
                var outputs = document.querySelectorAll(
                    '.shiny-bound-output, .html-widget, .plotly, .leaflet-container, .gt_table'
                );
                return outputs.length > 0;
            }""",
            timeout=SHINY_CONNECT_TIMEOUT,
        )
    except Exception:
        pass  # Continue — page may still have useful content

    time.sleep(wait)

    # 3. Wait until Shiny is not busy
    try:
        page.wait_for_function(
            "() => !document.querySelector('html.shiny-busy')",
            timeout=SHINY_BUSY_TIMEOUT,
        )
    except Exception:
        pass

    # 4. Widget-specific settle
    try:
        page.wait_for_function(
            """() => {
                var leaflets = document.querySelectorAll('.leaflet-container');
                for (var i = 0; i < leaflets.length; i++) {
                    if (!leaflets[i].querySelector('.leaflet-tile-loaded')) return false;
                }
                var plotlys = document.querySelectorAll('.plotly, .js-plotly-plot');
                for (var j = 0; j < plotlys.length; j++) {
                    if (!plotlys[j].querySelector('svg.main-svg')) return false;
                }
                return true;
            }""",
            timeout=10000,
        )
    except Exception:
        pass


def _capture_app_views(page: "Page", output_dir: str, prefix: str = "screenshot") -> list[str]:
    """Capture landing + every visible tab / nav-panel. Returns list of paths."""
    os.makedirs(output_dir, exist_ok=True)
    paths: list[str] = []

    landing = os.path.join(output_dir, f"{prefix}_01_landing.png")
    try:
        page.screenshot(path=landing, full_page=True, timeout=30000)
        paths.append(landing)
    except Exception as exc:
        print(f"WARNING: landing full_page screenshot failed: {exc}", file=sys.stderr)
        try:
            page.screenshot(path=landing, full_page=False, timeout=15000)
            paths.append(landing)
        except Exception as exc2:
            print(f"ERROR: landing viewport screenshot also failed: {exc2}", file=sys.stderr)
            return paths

    try:
        tabs = page.evaluate(_TAB_SELECTOR_JS) or []
    except Exception as exc:
        print(f"DEBUG: tab detection failed: {exc}", file=sys.stderr)
        tabs = []

    if not tabs:
        return paths

    print(f"Detected {len(tabs)} additional tab(s); capturing each.")
    tabs = tabs[:MAX_TAB_SCREENSHOTS]

    for ordinal, tab in enumerate(tabs, start=2):
        label = str(tab.get("label", f"tab-{ordinal}")) or f"tab-{ordinal}"
        idx = int(tab.get("index", -1))
        if idx < 0:
            continue
        slug = _slugify(label)
        target = os.path.join(output_dir, f"{prefix}_{ordinal:02d}_{slug}.png")

        try:
            clicked = page.evaluate(
                """(targetIdx) => {
                    const els = document.querySelectorAll(
                        '[data-bs-toggle="tab"],'
                        + '[data-bs-toggle="pill"],'
                        + '[data-toggle="tab"],'
                        + '[data-toggle="pill"],'
                        + '[role="tab"],'
                        + '.bslib-page-navbar .navbar-nav .nav-link,'
                        + '.shiny-tab-input ~ .nav .nav-link'
                    );
                    if (targetIdx < 0 || targetIdx >= els.length) return false;
                    els[targetIdx].click();
                    return true;
                }""",
                idx,
            )
            if not clicked:
                continue
        except Exception as exc:
            print(f"DEBUG: tab '{label}' click failed: {exc}", file=sys.stderr)
            continue

        _wait_for_shiny_render(page, wait=3)
        time.sleep(1)

        try:
            page.screenshot(path=target, full_page=True, timeout=30000)
            paths.append(target)
            print(f"  captured {os.path.basename(target)}")
        except Exception as exc:
            print(f"WARNING: tab '{label}' full_page screenshot failed: {exc}", file=sys.stderr)
            try:
                page.screenshot(path=target, full_page=False, timeout=15000)
                paths.append(target)
            except Exception as exc2:
                print(f"WARNING: tab '{label}' viewport also failed: {exc2}", file=sys.stderr)

    return paths


def take_screenshot(
    port: int = 8000,
    output: str = "screenshot.png",
    wait: float = DEFAULT_WAIT,
) -> None:
    """Capture every tab/view of the Shiny app at ``port``.

    Writes ``screenshot_NN_<slug>.png`` files into the directory of
    ``output``. For backwards compatibility the landing screenshot is also
    copied to ``output`` itself.
    """
    from playwright.sync_api import sync_playwright

    url = f"http://localhost:{port}"
    width, height = DEFAULT_VIEWPORT
    output_dir = os.path.dirname(os.path.abspath(output)) or "."

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        try:
            page.goto(url, timeout=15000)
        except Exception as exc:
            print(f"ERROR: Could not load {url}: {exc}", file=sys.stderr)
            browser.close()
            sys.exit(1)

        _wait_for_shiny_render(page, wait)

        paths = _capture_app_views(page, output_dir, prefix="screenshot")
        browser.close()

    if not paths:
        print("ERROR: no screenshots captured", file=sys.stderr)
        sys.exit(1)

    # Backwards-compat: also write the landing capture to the requested
    # ``--output`` path so older tooling that expects ``screenshot.png``
    # still finds something.
    landing = paths[0]
    if os.path.abspath(landing) != os.path.abspath(output):
        try:
            shutil.copy2(landing, output)
        except Exception as exc:
            print(f"WARNING: could not copy landing to {output}: {exc}", file=sys.stderr)

    print(f"Captured {len(paths)} screenshot(s):")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Take screenshots of every tab in a running Shiny app")
    parser.add_argument("--port", type=int, default=8000, help="App port (default: 8000)")
    parser.add_argument("--output", default="/home/user/project/screenshot.png", help="Backwards-compat landing-screenshot path; per-tab files land alongside it")
    parser.add_argument("--wait", type=float, default=DEFAULT_WAIT, help="Seconds to wait after load")
    args = parser.parse_args()
    take_screenshot(port=args.port, output=args.output, wait=args.wait)
