"""Contract tests for the prebuilt generation sandbox images."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILES = (
    REPO_ROOT / "src/shinygen/dockerfiles/Dockerfile.python",
    REPO_ROOT / "src/shinygen/dockerfiles/Dockerfile.r",
)


def test_agent_cli_versions_are_current_and_consistent():
    for dockerfile in DOCKERFILES:
        contents = dockerfile.read_text(encoding="utf-8")
        assert "ARG CLAUDE_VERSION=2.1.227" in contents
        assert "ARG CODEX_VERSION=rust-v0.147.0" in contents


def test_agent_cli_smoke_checks_fail_the_image_build_on_broken_binaries():
    for dockerfile in DOCKERFILES:
        contents = dockerfile.read_text(encoding="utf-8")
        assert "/usr/local/bin/claude --version || true" not in contents
        assert "/usr/local/bin/codex --version || true" not in contents

    workflow = (REPO_ROOT / ".github/workflows/build-sandbox-images.yml").read_text(
        encoding="utf-8"
    )
    assert "claude --version || true" not in workflow
    assert "codex --version || true" not in workflow
