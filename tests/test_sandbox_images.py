"""Regression checks for fast, self-contained benchmark sandboxes."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKER_DIR = ROOT / "src" / "shinygen" / "dockerfiles"


def test_r_image_does_not_install_python_dashboard_stack():
    dockerfile = (DOCKER_DIR / "Dockerfile.r").read_text(encoding="utf-8")

    assert "requirements-python.txt" not in dockerfile
    assert "shinywidgets" not in dockerfile
    assert "great-tables" not in dockerfile
    assert "geopandas" not in dockerfile


def test_python_image_preinstalls_every_documented_dashboard_dependency():
    requirements = (DOCKER_DIR / "requirements-python.txt").read_text(
        encoding="utf-8"
    )

    for package in (
        "shiny",
        "shinyswatch",
        "shinywidgets",
        "plotly",
        "faicons",
        "pandas",
        "matplotlib",
        "seaborn",
        "great-tables",
        "itables",
        "folium",
        "pydeck",
        "lonboard",
        "geopandas",
    ):
        assert package in requirements.splitlines()


def test_benchmark_prompt_forbids_runtime_dependency_installation():
    prompt = (ROOT / "src" / "shinygen" / "prompts.py").read_text(encoding="utf-8")

    assert "Do not install packages during benchmark runs" in prompt
    assert "Install any additional Python packages you need" not in prompt


def test_image_build_smoke_tests_preinstalled_framework_dependencies():
    workflow = (ROOT / ".github" / "workflows" / "build-sandbox-images.yml").read_text(
        encoding="utf-8"
    )

    assert "import shiny, shinywidgets, plotly, pandas, geopandas, playwright" in workflow
    assert 'library(shiny); library(bslib); library(leaflet); library(plotly)' in workflow
