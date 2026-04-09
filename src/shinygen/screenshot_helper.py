"""
Screenshot helper — takes a full-page screenshot of a running Shiny app.

Usage:
    python screenshot_helper.py [--port PORT] [--output PATH] [--wait SECONDS]

Pre-installed inside the Docker sandbox. Used by the agent for visual
self-evaluation of generated Shiny apps.

NOTE: The Shiny-wait logic here mirrors screenshot.py (host-side).
Both use the same viewport and wait strategy. Keep them in sync.
"""

import argparse
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

# Shared viewport/wait constants (mirrored from config.py for standalone use)
DEFAULT_VIEWPORT = (1920, 1080)
DEFAULT_WAIT = 5.0
SHINY_CONNECT_TIMEOUT = 20000  # ms
SHINY_BUSY_TIMEOUT = 10000  # ms


def _wait_for_shiny_render(page: "Page", wait: float = DEFAULT_WAIT) -> None:
    """Wait for Shiny to connect and render outputs.

    This shared logic is used by both the in-sandbox helper and
    the host-side screenshot module.
    """
    # Wait for Shiny connection + bound outputs
    try:
        page.wait_for_function(
            """() => {
                if (typeof Shiny === 'undefined') return false;
                var outputs = document.querySelectorAll(
                    '.shiny-bound-output, .html-widget, .plotly'
                );
                return outputs.length > 0;
            }""",
            timeout=SHINY_CONNECT_TIMEOUT,
        )
    except Exception:
        pass  # Continue — page may still have useful content

    time.sleep(wait)

    # Wait until Shiny is not busy
    try:
        page.wait_for_function(
            "() => !document.querySelector('html.shiny-busy')",
            timeout=SHINY_BUSY_TIMEOUT,
        )
    except Exception:
        pass


def take_screenshot(
    port: int = 8000,
    output: str = "screenshot.png",
    wait: float = DEFAULT_WAIT,
) -> None:
    from playwright.sync_api import sync_playwright

    url = f"http://localhost:{port}"
    width, height = DEFAULT_VIEWPORT

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

        page.screenshot(path=output, full_page=True)
        print(f"Screenshot saved to {output}")
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Take a screenshot of a running Shiny app")
    parser.add_argument("--port", type=int, default=8000, help="App port (default: 8000)")
    parser.add_argument("--output", default="/home/user/project/screenshot.png", help="Output path")
    parser.add_argument("--wait", type=float, default=5.0, help="Seconds to wait after load")
    args = parser.parse_args()
    take_screenshot(port=args.port, output=args.output, wait=args.wait)
