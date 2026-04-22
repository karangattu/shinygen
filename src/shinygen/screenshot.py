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


def take_screenshots(
    app_dir: Path,
    framework_key: str,
    port: int | None = None,
    output_dir: Path | None = None,
) -> Path | None:
    """Take a full-page screenshot of a Shiny app.

    Args:
        app_dir: Directory containing the app file.
        framework_key: "shiny_python" or "shiny_r".
        port: Port to use (default: BASE_PORT).
        output_dir: Where to save screenshots (default: app_dir).

    Returns:
        Path to the screenshot, or None if it failed.
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
    screenshot_path = output_dir / "screenshot.png"

    proc = start_app(app_dir, artifact, language, port)
    width, height = SCREENSHOT_VIEWPORT

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})

            url = f"http://localhost:{port}"
            if not wait_for_shiny(page, url):
                browser.close()
                return None

            # Wait for any deferred rendering
            time.sleep(POST_INTERACT_WAIT)

            # Full-page screenshot. If the page is so tall that Chromium
            # refuses to capture it (rare but seen with massive maps/tables),
            # fall back to a viewport-only screenshot so the benchmark still
            # has *something* to judge.
            try:
                page.screenshot(
                    path=str(screenshot_path),
                    full_page=True,
                    timeout=30000,
                )
            except Exception as exc:
                logger.warning(
                    "full_page screenshot failed (%s); falling back to viewport.",
                    exc,
                )
                try:
                    page.screenshot(
                        path=str(screenshot_path),
                        full_page=False,
                        timeout=15000,
                    )
                except Exception as exc2:
                    logger.warning("viewport screenshot also failed: %s", exc2)
                    browser.close()
                    return None

            browser.close()

        return screenshot_path

    except Exception as exc:
        logger.warning("Screenshot capture failed: %s", exc)
        return None
    finally:
        stop_app(proc)
