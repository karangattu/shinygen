"""Static checks for GitHub Action versions used in workflows."""

from pathlib import Path


WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _read_workflow(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def test_build_sandbox_images_workflow_uses_node24_compatible_docker_actions():
    workflow = _read_workflow("build-sandbox-images.yml")

    assert "docker/setup-buildx-action@v4" in workflow
    assert "docker/login-action@v4" in workflow
    assert "docker/metadata-action@v6" in workflow
    assert "docker/build-push-action@v7" in workflow


def test_run_workflows_use_node24_compatible_docker_login_action():
    workflow_names = [
        "run-benchmark-matrix.yml",
        "run-shinygen.yml",
        "run-shinygen-multi.yml",
    ]

    for workflow_name in workflow_names:
        workflow = _read_workflow(workflow_name)
        assert "docker/login-action@v4" in workflow, workflow_name


def test_workflows_do_not_force_node24_runtime_override():
    workflow_names = [
        "build-sandbox-images.yml",
        "run-benchmark-matrix.yml",
        "run-shinygen.yml",
        "run-shinygen-multi.yml",
    ]

    for workflow_name in workflow_names:
        workflow = _read_workflow(workflow_name)
        assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24" not in workflow, workflow_name
