"""Tests for shinygen.api."""

from pathlib import Path

from shinygen import api
from shinygen.api import BatchJob
from shinygen.iterate import GenerationResult


def test_generate_data_csv_loaded(tmp_path, monkeypatch):
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("x,y\n1,2\n", encoding="utf-8")
    captured = {}

    def fake_generate_and_refine(**kwargs):
        captured.update(kwargs)
        return GenerationResult()

    monkeypatch.setattr(api, "generate_and_refine", fake_generate_and_refine)

    api.generate(prompt="build app", data_csv=csv_path)

    assert captured["data_files"] == {"sales.csv": "x,y\n1,2\n"}


def test_generate_data_csv_overrides_matching_data_files(tmp_path, monkeypatch):
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("x,y\n9,10\n", encoding="utf-8")
    captured = {}

    def fake_generate_and_refine(**kwargs):
        captured.update(kwargs)
        return GenerationResult()

    monkeypatch.setattr(api, "generate_and_refine", fake_generate_and_refine)

    api.generate(
        prompt="build app",
        data_csv=Path(csv_path),
        data_files={"sales.csv": "old\n", "meta.json": '{"k":"v"}\n'},
    )

    assert captured["data_files"]["sales.csv"] == "x,y\n9,10\n"
    assert captured["data_files"]["meta.json"] == '{"k":"v"}\n'


def test_batch_runs_all_jobs(monkeypatch):
    calls = []

    def fake_generate_and_refine(**kwargs):
        calls.append(kwargs)
        return GenerationResult(
            app_dir=Path(kwargs["output_dir"]), score=8.0, passed=True
        )

    monkeypatch.setattr(api, "generate_and_refine", fake_generate_and_refine)

    result = api.batch([
        {"prompt": "app one", "model": "claude-sonnet", "output_dir": "./out1"},
        {"prompt": "app two", "model": "gpt54", "output_dir": "./out2"},
    ])

    assert len(result.results) == 2
    assert result.succeeded == 2
    assert result.failed == 0
    assert calls[0]["model"] == "claude-sonnet"
    assert calls[1]["model"] == "gpt54"


def test_batch_accepts_csv_file_alias(tmp_path, monkeypatch):
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("x,y\n1,2\n", encoding="utf-8")
    calls = []

    def fake_generate_and_refine(**kwargs):
        calls.append(kwargs)
        return GenerationResult(app_dir=Path("out"), score=8.0, passed=True)

    monkeypatch.setattr(api, "generate_and_refine", fake_generate_and_refine)

    result = api.batch([
        {"prompt": "app one", "csv_file": str(csv_path), "output_dir": "./out1"},
    ])

    assert result.succeeded == 1
    assert calls[0]["data_files"] == {"sales.csv": "x,y\n1,2\n"}


def test_batch_with_batch_job_objects(monkeypatch):
    calls = []

    def fake_generate_and_refine(**kwargs):
        calls.append(kwargs)
        return GenerationResult(
            app_dir=Path(kwargs["output_dir"]), score=7.0, passed=True
        )

    monkeypatch.setattr(api, "generate_and_refine", fake_generate_and_refine)

    jobs = [
        BatchJob(prompt="dashboard", model="claude-opus", output_dir="./a"),
        BatchJob(prompt="dashboard", model="gpt54-mini", output_dir="./b",
                 screenshot=True),
    ]
    result = api.batch(jobs)

    assert len(result.results) == 2
    assert result.succeeded == 2
    assert calls[1]["screenshot"] is True


def test_batch_records_failures(monkeypatch):
    call_count = 0

    def fake_generate_and_refine(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return GenerationResult(error="docker timeout")
        return GenerationResult(app_dir=Path("ok"), score=9.0, passed=True)

    monkeypatch.setattr(api, "generate_and_refine", fake_generate_and_refine)

    result = api.batch([
        {"prompt": "a", "output_dir": "./x"},
        {"prompt": "b", "output_dir": "./y"},
    ])

    assert result.failed == 1
    assert result.succeeded == 1
    assert result.results[0].error == "docker timeout"


def test_batch_handles_exception(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(api, "generate_and_refine", boom)

    result = api.batch([{"prompt": "fail", "output_dir": "./z"}])

    assert result.failed == 1
    assert result.succeeded == 0
    assert "kaboom" in result.results[0].error

