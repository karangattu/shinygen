"""
Playwright-based screenshot automation for generated Shiny apps.
Takes a single full-page screenshot after the app has rendered.

NOTE: This module runs on the HOST. The in-sandbox screenshot helper
(screenshot_helper.py) shares the same Shiny-wait logic via
_wait_for_shiny_render(). Both should stay in sync.
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from .config import (
    BASE_PORT,
    FRAMEWORKS,
    PAGE_LOAD_WAIT,
    POST_INTERACT_WAIT,
    SCREENSHOT_VIEWPORT,
    STARTUP_TIMEOUT,
)

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)


def wait_for_port(port: int, timeout: int = STARTUP_TIMEOUT) -> bool:
    """Wait for a TCP port to become available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


def start_app(
    app_dir: Path,
    app_file: str,
    language: str,
    port: int,
) -> subprocess.Popen:
    """Start a Shiny app server. Returns the subprocess."""
    if language.lower() == "python":
        cmd = [
            sys.executable,
            "-m",
            "shiny",
            "run",
            app_file,
            "--port",
            str(port),
        ]
    else:
        r_expr = f"shiny::runApp('{app_file}', " f"port={port}, launch.browser=FALSE)"
        cmd = ["Rscript", "-e", r_expr]

    proc = subprocess.Popen(
        cmd,
        cwd=str(app_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,
    )
    return proc


def stop_app(proc: subprocess.Popen) -> None:
    """Stop the app process and all its children."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _write_process_log(proc: subprocess.Popen, destination: Path) -> None:
    """Persist captured app stdout/stderr for screenshot diagnostics."""
    try:
        stdout, stderr = proc.communicate(timeout=1)
    except Exception as exc:  # pragma: no cover - process-state dependent
        logger.debug("Could not collect app process output: %s", exc)
        return

    stdout_text = (
        stdout.decode("utf-8", errors="replace")
        if isinstance(stdout, bytes)
        else (stdout or "")
    )
    stderr_text = (
        stderr.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes)
        else (stderr or "")
    )
    if not stdout_text and not stderr_text:
        return

    destination.write_text(
        "# Host-side screenshot app log\n\n"
        "## stdout\n"
        f"{stdout_text}\n\n"
        "## stderr\n"
        f"{stderr_text}\n",
        encoding="utf-8",
    )


def _wait_for_shiny_render(page: "Page", wait: float = PAGE_LOAD_WAIT) -> None:
    """Wait for Shiny to connect and render outputs.

    Strategy (each step is best-effort, never raises):
      1. Wait for the network to go idle (tiles, fonts, JS bundles).
      2. Wait for Shiny + at least one bound output to exist.
      3. Sleep ``wait`` seconds for deferred async renders (Plotly, leaflet,
         great_tables HTML, etc.).
      4. Wait until ``html.shiny-busy`` is gone.
      5. Wait for any leaflet/plotly/observable widgets to finish layout.

    Mirrors the same logic in screenshot_helper.py (in-sandbox).
    """
    # 1. Network idle (tiles, fonts, JS) — generous timeout, ignore failure
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception as exc:
        logger.debug("networkidle wait timed out: %s", exc)

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
            timeout=20000,
        )
    except Exception as exc:
        logger.debug("Shiny connect wait timed out: %s", exc)

    time.sleep(wait)

    # 3. Wait until not busy
    try:
        page.wait_for_function(
            "() => !document.querySelector('html.shiny-busy')",
            timeout=10000,
        )
    except Exception as exc:
        logger.debug("Shiny busy-wait timed out: %s", exc)

    # 4. Widget-specific settle: every leaflet must have tiles loaded,
    #    every plotly must have its main svg drawn.
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
    except Exception as exc:
        logger.debug("widget settle wait timed out: %s", exc)


def wait_for_shiny(page: "Page", url: str, timeout: int = 45) -> bool:
    """Navigate to the app and wait for Shiny to connect and render."""
    port = int(url.split(":")[-1])
    if not wait_for_port(port, timeout=30):
        return False

    try:
        page.goto(url, timeout=15000)
    except Exception as exc:
        logger.warning("Failed to navigate to %s: %s", url, exc)
        return False

    _wait_for_shiny_render(page)

    time.sleep(1)
    return True


# ---------------------------------------------------------------------------
# Multi-tab capture
# ---------------------------------------------------------------------------

# Maximum number of tab/nav screenshots to capture per app (in addition to the
# landing page). Caps both runtime cost and judge token usage. 8 covers the
# vast majority of real dashboards (most multi-tab apps use 3-5 tabs).
MAX_TAB_SCREENSHOTS = 8

# Selectors that match Shiny / bslib / Bootstrap tab and navbar links.
# Covers ``ui.navset_tab``, ``ui.navset_pill``, ``ui.navset_card_tab``,
# ``ui.page_navbar`` (bslib + bs5) and the older shinydashboard sidebar.
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
        // Skip already-active tab; landing screenshot already covers it.
        if (el.classList.contains('active') || el.getAttribute('aria-selected') === 'true') {
            return;
        }
        // Skip dropdown toggles — they don't reveal a panel directly.
        if (el.classList.contains('dropdown-toggle')) {
            return;
        }
        // De-dup by href/target so navbar + sidebar twins of the same tab
        // do not produce two screenshots.
        const key = (el.getAttribute('href') || '')
            + '|' + (el.getAttribute('data-bs-target') || '')
            + '|' + (el.getAttribute('data-value') || '')
            + '|' + (el.textContent || '').trim();
        if (!key || seen.has(key)) return;
        // Skip invisible nav items (display:none collapsed menus).
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
    """Turn a tab label into a filesystem-safe slug."""
    import re

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-").lower()
    return slug[:32] or "tab"


def _capture_app_views(
    page: "Page",
    output_dir: Path,
    prefix: str = "screenshot",
) -> list[Path]:
    """Capture the landing page plus every detected tab / nav-panel.

    Returns a sorted list of screenshot paths. The first entry is always the
    landing page; subsequent entries are one per tab in the order they appear
    in the DOM, capped at ``MAX_TAB_SCREENSHOTS``.

    Multi-tab dashboards otherwise get judged on landing-page only, which
    biases scores against `page_navbar` / `navset_*` apps. This function
    gives the judge full coverage of the app surface.
    """
    paths: list[Path] = []

    landing = output_dir / f"{prefix}_01_landing.png"
    try:
        page.screenshot(path=str(landing), full_page=True, timeout=30000)
        paths.append(landing)
    except Exception as exc:
        logger.warning(
            "landing full_page screenshot failed (%s); viewport fallback", exc
        )
        try:
            page.screenshot(path=str(landing), full_page=False, timeout=15000)
            paths.append(landing)
        except Exception as exc2:
            logger.warning("landing viewport screenshot also failed: %s", exc2)
            return paths

    # Detect tabs/nav links to visit.
    try:
        tabs = page.evaluate(_TAB_SELECTOR_JS) or []
    except Exception as exc:
        logger.debug("tab detection failed: %s", exc)
        tabs = []

    if not tabs:
        return paths

    logger.info("Detected %d additional tab(s) for multi-view capture", len(tabs))
    tabs = tabs[:MAX_TAB_SCREENSHOTS]

    for ordinal, tab in enumerate(tabs, start=2):
        label = str(tab.get("label", f"tab-{ordinal}")) or f"tab-{ordinal}"
        idx = int(tab.get("index", -1))
        if idx < 0:
            continue
        slug = _slugify(label)
        target = output_dir / f"{prefix}_{ordinal:02d}_{slug}.png"

        try:
            # Click by re-querying with the same selector list and indexing
            # — keeps the helper resilient to nodes detaching between calls.
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
                logger.debug(
                    "tab '%s' (idx=%d) was not clickable; skipping", label, idx
                )
                continue
        except Exception as exc:
            logger.debug("tab '%s' click failed: %s", label, exc)
            continue

        # Give Shiny time to swap the panel + render any deferred outputs.
        _wait_for_shiny_render(page, wait=3)
        time.sleep(1)

        try:
            page.screenshot(path=str(target), full_page=True, timeout=30000)
            paths.append(target)
        except Exception as exc:
            logger.warning(
                "tab '%s' full_page screenshot failed (%s); viewport fallback",
                label,
                exc,
            )
            try:
                page.screenshot(path=str(target), full_page=False, timeout=15000)
                paths.append(target)
            except Exception as exc2:
                logger.warning(
                    "tab '%s' viewport screenshot also failed: %s", label, exc2
                )

    return paths


def take_screenshots(
    app_dir: Path,
    framework_key: str,
    port: int | None = None,
    output_dir: Path | None = None,
) -> list[Path]:
    """Take full-page screenshots of a Shiny app, one per tab/view.

    Always captures the landing page; additionally clicks through any
    detected tab / nav-panel links (``ui.navset_*``, ``ui.page_navbar``,
    bslib/Bootstrap tabs) and captures each view, capped at
    ``MAX_TAB_SCREENSHOTS``.

    Args:
        app_dir: Directory containing the app file.
        framework_key: "shiny_python" or "shiny_r".
        port: Port to use (default: BASE_PORT).
        output_dir: Where to save screenshots (default: app_dir).

    Returns:
        Sorted list of screenshot paths. Empty list if capture failed.
        The first entry is always the landing page.
    """
    from playwright.sync_api import sync_playwright

    if port is None:
        port = BASE_PORT
    if output_dir is None:
        output_dir = app_dir

    fw = FRAMEWORKS[framework_key]
    artifact = fw["primary_artifact"]
    language = fw["language"]

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        proc = start_app(app_dir, artifact, language, port)
    except Exception as exc:
        logger.warning("Failed to start app for screenshot capture: %s", exc)
        return []
    width, height = SCREENSHOT_VIEWPORT

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})

            url = f"http://localhost:{port}"
            if not wait_for_shiny(page, url):
                browser.close()
                return []

            time.sleep(POST_INTERACT_WAIT)

            paths = _capture_app_views(page, output_dir, prefix="screenshot")

            browser.close()
            return paths

    except Exception as exc:
        logger.warning("Screenshot capture failed: %s", exc)
        return []
    finally:
        stop_app(proc)
        _write_process_log(proc, output_dir / "host_app.log")
