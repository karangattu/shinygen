"""Tests for shinygen.cli."""

import json
from pathlib import Path

from click.testing import CliRunner

from shinygen import api
from shinygen.api import BatchResult
from shinygen.cli import main
from shinygen.iterate import GenerationResult


def test_generate_cli_csv_file_loaded(tmp_path, monkeypatch):
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return GenerationResult(app_dir=Path("output"), score=5.0, iterations=1, passed=True)

    monkeypatch.setattr(api, "generate", fake_generate)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["generate", "--prompt", "build app", "--csv-file", str(csv_path)],
    )

    assert result.exit_code == 0, result.output
    assert captured["data_files"] == {"sales.csv": "a,b\n1,2\n"}


def test_generate_cli_csv_file_overrides_data_file(tmp_path, monkeypatch):
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()

    data_csv_from_data_file = d1 / "sales.csv"
    data_csv_from_csv_file = d2 / "sales.csv"
    meta = tmp_path / "meta.json"

    data_csv_from_data_file.write_text("old\n", encoding="utf-8")
    data_csv_from_csv_file.write_text("new\n", encoding="utf-8")
    meta.write_text('{"ok":true}\n', encoding="utf-8")

    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return GenerationResult(app_dir=Path("output"), score=5.0, iterations=1, passed=True)

    monkeypatch.setattr(api, "generate", fake_generate)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "generate",
            "--prompt",
            "build app",
            "--data-file",
            str(data_csv_from_data_file),
            "--data-file",
            str(meta),
            "--csv-file",
            str(data_csv_from_csv_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["data_files"]["sales.csv"] == "new\n"
    assert captured["data_files"]["meta.json"] == '{"ok":true}\n'


def test_batch_cli_runs_jobs(tmp_path, monkeypatch):
    config_path = tmp_path / "batch.json"
    config_path.write_text(
        json.dumps([
            {"prompt": "app1", "model": "claude-sonnet", "output_dir": str(tmp_path / "out1")},
            {"prompt": "app2", "model": "gpt54", "output_dir": str(tmp_path / "out2")},
        ]),
        encoding="utf-8",
    )

    calls = []

    def fake_batch(jobs):
        calls.extend(jobs)
        return BatchResult(
            results=[
                GenerationResult(app_dir=Path(j["output_dir"]), score=8.0, passed=True)
                for j in jobs
            ],
            succeeded=len(jobs),
            failed=0,
        )

    monkeypatch.setattr(api, "batch", fake_batch)

    runner = CliRunner()
    result = runner.invoke(main, ["batch", "--config", str(config_path)])

    assert result.exit_code == 0, result.output
    assert "2 succeeded" in result.output
    assert len(calls) == 2


def test_batch_cli_resolves_relative_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_path = data_dir / "sales.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")

    config_path = tmp_path / "batch.json"
    config_path.write_text(
        json.dumps([
            {
                "prompt": "app1",
                "model": "claude-sonnet",
                "output_dir": "./out1",
                "csv_file": "./data/sales.csv",
            }
        ]),
        encoding="utf-8",
    )

    captured = []

    def fake_batch(jobs):
        captured.extend(jobs)
        return BatchResult(
            results=[GenerationResult(app_dir=Path(jobs[0]["output_dir"]), passed=True)],
            succeeded=1,
            failed=0,
        )

    monkeypatch.setattr(api, "batch", fake_batch)

    runner = CliRunner()
    result = runner.invoke(main, ["batch", "--config", str(config_path)])

    assert result.exit_code == 0, result.output
    assert captured[0]["csv_file"] == str(csv_path)
    assert captured[0]["output_dir"] == str(tmp_path / "out1")


def test_batch_cli_rejects_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["batch", "--config", str(bad)])

    assert result.exit_code != 0
    assert "Invalid JSON" in result.output


def test_batch_cli_rejects_non_array(tmp_path):
    config_path = tmp_path / "obj.json"
    config_path.write_text('{"prompt": "hi"}', encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["batch", "--config", str(config_path)])

    assert result.exit_code != 0
    assert "JSON array" in result.output

