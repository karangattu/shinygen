from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FAIL_MARKERS = (
    "Traceback (most recent call last):",
    "TypeError:",
    "ValueError:",
    "NameError:",
    "ImportError:",
    "ModuleNotFoundError:",
    "SyntaxError:",
    "Error in ",
    "Execution halted",
)

SHINY_HTML_MARKERS = (
    "shiny",
    "html",
    "<script",
    "<body",
    "<!doctype",
)


def _check_logs_for_failure(log_path: Path) -> str | None:
    if not log_path.exists():
        return None
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        for marker in FAIL_MARKERS:
            if marker in content:
                return f"Found error signature '{marker}' in {log_path}"
    except Exception:
        pass
    return None


def validate_app(
    target_file: str | None = None,
    port: int = 8000,
    timeout: float = 12.0,
    log_path: str = "/tmp/app.log",
) -> int:
    current_dir = Path.cwd()
    if target_file:
        app_file = current_dir / target_file
    elif (current_dir / "app.py").exists():
        app_file = current_dir / "app.py"
    elif (current_dir / "app.R").exists():
        app_file = current_dir / "app.R"
    else:
        print("[SHINYGEN VALIDATION FAILED] Neither app.py nor app.R found in working directory.")
        return 1

    log_file = Path(log_path)
    log_file.unlink(missing_ok=True)

    is_r = app_file.suffix.lower() == ".r"
    if is_r:
        cmd = [
            "Rscript",
            "-e",
            f"shiny::runApp('{app_file.name}', port={port}, launch.browser=FALSE)",
        ]
    else:
        cmd = [
            sys.executable,
            "-m",
            "shiny",
            "run",
            app_file.name,
            "--port",
            str(port),
        ]

    log_handle = open(log_file, "w", encoding="utf-8", errors="replace")
    process = None
    try:
        process = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=str(current_dir),
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

        start_time = time.time()
        url = f"http://127.0.0.1:{port}/"
        responded = False
        html_valid = False

        while time.time() - start_time < timeout:
            if process.poll() is not None:
                log_handle.flush()
                print(f"[SHINYGEN VALIDATION FAILED] Process exited prematurely with status {process.returncode}.")
                _print_log_tail(log_file)
                return 1

            try:
                req = urllib.request.Request(url, headers={"User-Agent": "shinygen-validator"})
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        responded = True
                        body = resp.read(65536).decode("utf-8", errors="replace").lower()
                        if any(marker in body for marker in SHINY_HTML_MARKERS):
                            html_valid = True
                            break
            except Exception:
                pass
            time.sleep(0.5)

        log_handle.flush()
        err_in_logs = _check_logs_for_failure(log_file)

        if responded and html_valid and not err_in_logs:
            print(f"[SHINYGEN VALIDATION SUCCESS] App '{app_file.name}' started and rendered valid Shiny HTML on port {port}.")
            return 0

        print(f"[SHINYGEN VALIDATION FAILED] Validation failed for '{app_file.name}'.")
        if not responded:
            print(f"  - App did not respond with HTTP 200 on port {port} within {timeout}s.")
        elif not html_valid:
            print("  - App responded, but response content lacked valid Shiny HTML elements.")
        if err_in_logs:
            print(f"  - {err_in_logs}")

        _print_log_tail(log_file)
        return 1

    finally:
        if process is not None and process.poll() is None:
            try:
                if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                process.wait(timeout=3)
            except Exception:
                try:
                    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
                except Exception:
                    pass
        log_handle.close()


def _print_log_tail(log_file: Path, max_lines: int = 80) -> None:
    if not log_file.exists():
        return
    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-max_lines:] if len(lines) > max_lines else lines
        print("\n--- SERVER LOG TAIL ---")
        for line in tail:
            print(line)
        print("-----------------------\n")
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Shiny app startup validator")
    parser.add_argument("--app", default=None, help="App file (app.py or app.R)")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--timeout", type=float, default=12.0, help="Startup timeout in seconds")
    parser.add_argument("--log", default="/tmp/app.log", help="Path to log file")
    args = parser.parse_args()

    code = validate_app(
        target_file=args.app,
        port=args.port,
        timeout=args.timeout,
        log_path=args.log,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
