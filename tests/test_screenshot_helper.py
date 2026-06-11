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

    def test_default_wait_matches_config(self):
        from shinygen.config import PAGE_LOAD_WAIT

        assert DEFAULT_WAIT == PAGE_LOAD_WAIT == 7.0

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

        # Should not raise. _wait_for_shiny_render now performs three
        # wait_for_function calls: Shiny-connect, busy-flag, and a
        # widget-settle pass for leaflet/plotly.
        _wait_for_shiny_render(page, wait=0.01)
        assert page.wait_for_function.call_count == 3


class TestWaitForPort:
    def test_wait_for_port_success(self):
        import socket
        import threading
        from shinygen.screenshot_helper import wait_for_port

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
        s.listen(1)

        def accept_conn():
            try:
                conn, _ = s.accept()
                conn.close()
            except Exception:
                pass
            finally:
                s.close()

        t = threading.Thread(target=accept_conn)
        t.start()

        try:
            assert wait_for_port(port, timeout=5.0) is True
        finally:
            s.close()
            t.join()

    def test_wait_for_port_failure(self):
        import socket
        from shinygen.screenshot_helper import wait_for_port

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
        s.close()

        assert wait_for_port(port, timeout=0.1) is False
