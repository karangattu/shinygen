"""Tests for shinygen.screenshot_helper"""

from shinygen.screenshot_helper import (
    DEFAULT_VIEWPORT,
    DEFAULT_WAIT,
    SHINY_BUSY_TIMEOUT,
    SHINY_CONNECT_TIMEOUT,
)


class TestConstants:
    def test_viewport_matches_config(self):
        from shinygen.config import SCREENSHOT_VIEWPORT

        assert DEFAULT_VIEWPORT == SCREENSHOT_VIEWPORT

    def test_default_wait_positive(self):
        assert DEFAULT_WAIT > 0

    def test_timeouts_positive(self):
        assert SHINY_CONNECT_TIMEOUT > 0
        assert SHINY_BUSY_TIMEOUT > 0


class TestWaitForShinyRender:
    def test_handles_timeout_gracefully(self):
        """_wait_for_shiny_render should not raise even if waits time out."""
        from unittest.mock import MagicMock

        from shinygen.screenshot_helper import _wait_for_shiny_render

        page = MagicMock()
        page.wait_for_function.side_effect = TimeoutError("timed out")

        # Should not raise
        _wait_for_shiny_render(page, wait=0.01)
        assert page.wait_for_function.call_count == 2
