"""Tests for shinygen.api."""

from pathlib import Path

import pytest

from shinygen import api
from shinygen.api import BatchJob, read_data_files
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

    result = api.batch(
        [
            {"prompt": "app one", "model": "claude-sonnet", "output_dir": "./out1"},
            {"prompt": "app two", "model": "gpt54", "output_dir": "./out2"},
        ]
    )

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

    result = api.batch(
        [
            {"prompt": "app one", "csv_file": str(csv_path), "output_dir": "./out1"},
        ]
    )

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
        BatchJob(
            prompt="dashboard", model="gpt54-mini", output_dir="./b", screenshot=True
        ),
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

    result = api.batch(
        [
            {"prompt": "a", "output_dir": "./x"},
            {"prompt": "b", "output_dir": "./y"},
        ]
    )

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


class TestReadDataFiles:
    def test_returns_none_when_no_inputs(self):
        assert read_data_files() is None

    def test_returns_data_files_dict_unchanged(self):
        data = {"file.txt": "content"}
        result = read_data_files(data_files=data)
        assert result == {"file.txt": "content"}

    @pytest.mark.parametrize(
        "filename", ["../outside.txt", "/tmp/outside.txt", "dir/data.csv"]
    )
    def test_rejects_unsafe_data_file_names(self, filename):
        with pytest.raises(ValueError, match="Unsafe data filename"):
            read_data_files(data_files={filename: "content"})

    def test_reads_csv_file(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("a,b\n1,2\n", encoding="utf-8")

        result = read_data_files(data_csv=csv_path)
        assert result == {"data.csv": "a,b\n1,2\n"}

    def test_reads_data_file_paths(self, tmp_path):
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        f1.write_text("content1", encoding="utf-8")
        f2.write_text("content2", encoding="utf-8")

        result = read_data_files(data_file_paths=[f1, f2])
        assert result == {"file1.txt": "content1", "file2.txt": "content2"}

    def test_csv_overrides_data_file_paths_with_same_name(self, tmp_path):
        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()

        f1 = d1 / "data.csv"
        f2 = d2 / "data.csv"
        f1.write_text("old", encoding="utf-8")
        f2.write_text("new", encoding="utf-8")

        result = read_data_files(data_file_paths=[f1], data_csv=f2)
        assert result == {"data.csv": "new"}

    def test_merges_all_sources(self, tmp_path):
        csv_path = tmp_path / "sales.csv"
        txt_path = tmp_path / "meta.txt"
        csv_path.write_text("csv_content", encoding="utf-8")
        txt_path.write_text("txt_content", encoding="utf-8")

        result = read_data_files(
            data_files={"existing.json": '{"k":"v"}'},
            data_file_paths=[txt_path],
            data_csv=csv_path,
        )

        assert result == {
            "existing.json": '{"k":"v"}',
            "meta.txt": "txt_content",
            "sales.csv": "csv_content",
        }

    def test_accepts_string_paths(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("content", encoding="utf-8")

        result = read_data_files(data_csv=str(csv_path))
        assert result == {"data.csv": "content"}
