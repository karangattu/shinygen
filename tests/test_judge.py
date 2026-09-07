"""Tests for shinygen.judge"""

import json
import sys
import types
from pathlib import Path

import pytest

from shinygen.judge import (
    VISUAL_QA_DOCUMENTS,
    VISUAL_QA_SKILL_DIR,
    JudgeResult,
    _build_judge_message,
    _build_judge_system,
    _judge_with_openai,
    _retry_with_backoff,
    judge_app_with_api,
    parse_judge_response,
)


class TestParseJudgeResponse:
    def test_valid_json(self):
        response = json.dumps(
            {
                "requirement_fidelity": {"score": 7, "rationale": "Good coverage"},
                "code_maintainability": {"score": 8, "rationale": "Clean code"},
                "visual_ux_quality": {"score": 6, "rationale": "Plain but functional"},
                "code_robustness": {"score": 7, "rationale": "Handles edge cases"},
            }
        )
        result = parse_judge_response(response)
        assert result.composite == 7.0
        assert result.scores["requirement_fidelity"] == 7.0
        assert result.rationales["code_maintainability"] == "Clean code"

    def test_embedded_json(self):
        response = (
            "Here is my evaluation:\n"
            + json.dumps(
                {
                    "requirement_fidelity": {"score": 8, "rationale": "All features"},
                    "code_maintainability": {"score": 9, "rationale": "Excellent"},
                    "visual_ux_quality": {"score": 8, "rationale": "Professional"},
                    "code_robustness": {"score": 9, "rationale": "Robust"},
                }
            )
            + "\nDone!"
        )
        result = parse_judge_response(response)
        assert result.composite == 8.5

    def test_invalid_response(self):
        result = parse_judge_response("This is not JSON at all")
        assert result.composite == 0.0
        assert len(result.scores) == 0

    def test_partial_criteria(self):
        response = json.dumps(
            {
                "requirement_fidelity": {"score": 3, "rationale": "Partial"},
            }
        )
        result = parse_judge_response(response)
        assert result.scores["requirement_fidelity"] == 3.0
        # Only 1 of 4 criteria provided, so composite = 3/4 = 0.75
        # because missing criteria default to 0
        assert result.composite == 3.0 / 4

    def test_invalid_scores_are_clamped(self):
        response = json.dumps(
            {
                "requirement_fidelity": {"score": 12, "rationale": "Too high"},
                "code_maintainability": {"score": -3, "rationale": "Too low"},
                "visual_ux_quality": {"score": "nan", "rationale": "Invalid"},
                "code_robustness": {"score": "invalid", "rationale": "Invalid"},
            }
        )

        result = parse_judge_response(response)

        assert result.scores == {
            "requirement_fidelity": 10.0,
            "code_maintainability": 0.0,
            "visual_ux_quality": 0.0,
            "code_robustness": 0.0,
        }
        assert result.composite == 2.5


class TestJudgeResult:
    def test_passed_threshold(self):
        result = JudgeResult(composite=8.0)
        assert result.passed

    def test_failed_threshold(self):
        result = JudgeResult(composite=6.5)
        assert not result.passed

    def test_feedback_dict(self):
        result = JudgeResult(
            scores={"requirement_fidelity": 7.0, "code_maintainability": 8.0},
            rationales={
                "requirement_fidelity": "Good",
                "code_maintainability": "Clean",
            },
        )
        feedback = result.feedback_dict()
        assert feedback["requirement_fidelity"]["score"] == 7.0
        assert feedback["requirement_fidelity"]["rationale"] == "Good"


class TestJudgePrompt:
    def test_visual_qa_documents_are_embedded_in_full(self):
        prompt = _build_judge_system()
        for name in VISUAL_QA_DOCUMENTS:
            assert (VISUAL_QA_SKILL_DIR / name).read_text(encoding="utf-8") in prompt
        assert "{visual_qa_skill}" not in prompt

    def test_skill_changes_are_read_on_next_evaluation(self, tmp_path, monkeypatch):
        monkeypatch.setattr("shinygen.judge.VISUAL_QA_SKILL_DIR", tmp_path)
        for name in VISUAL_QA_DOCUMENTS:
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"Original {name}", encoding="utf-8")
        first = _build_judge_system()
        (tmp_path / "SKILL.md").write_text("Revised visual policy", encoding="utf-8")
        second = _build_judge_system()
        assert "Original SKILL.md" in first
        assert "Original SKILL.md" not in second
        assert "Revised visual policy" in second

    def test_missing_skill_reference_fails_instead_of_using_stale_rubric(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("shinygen.judge.VISUAL_QA_SKILL_DIR", tmp_path)
        (tmp_path / "SKILL.md").write_text("Skill present", encoding="utf-8")
        with pytest.raises(FileNotFoundError):
            _build_judge_system()

    def test_judge_message_requests_design_principle_based_evaluation(self):
        message = _build_judge_message("print('hello')")

        assert "good UI design practices" in message
        assert "design principle" in message
        assert "lower confidence" in message

    def test_visual_ux_rubric_is_calibrated_to_human_dashboard_preferences(self):
        prompt = _build_judge_system()
        for phrase in [
            "one-screen usefulness",
            "conventional Shiny",
            "prominent primary visualization",
            "Clean alone is not enough",
            "stuck loading indicators",
        ]:
            assert phrase in prompt

    def test_secondary_views_do_not_override_landing_judgment(self):
        message = _build_judge_message(
            "app", [Path("01-main.png"), Path("02-detail.png")]
        )
        assert "landing view independently first" in message
        assert "01-main.png" in message and "02-detail.png" in message
        assert "deserves credit for that breadth" not in message


class TestOpenAIJudgeRequest:
    def test_luna_uses_high_reasoning_and_max_completion_tokens(self, monkeypatch):
        captured: dict[str, object] = {}

        class FakeUsage:
            prompt_tokens = 123
            completion_tokens = 45

        class FakeMessage:
            content = json.dumps(
                {
                    "requirement_fidelity": {"score": 7, "rationale": "Good"},
                    "code_maintainability": {"score": 7, "rationale": "Clean"},
                    "visual_ux_quality": {"score": 7, "rationale": "Solid"},
                    "code_robustness": {"score": 7, "rationale": "Robust"},
                }
            )

        class FakeChoice:
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]
            usage = FakeUsage()

        class FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return FakeResponse()

        class FakeChat:
            completions = FakeCompletions()

        class FakeOpenAIClient:
            def __init__(self):
                self.chat = FakeChat()

        fake_openai_module = types.SimpleNamespace(OpenAI=FakeOpenAIClient)
        monkeypatch.setitem(sys.modules, "openai", fake_openai_module)

        result = _judge_with_openai(
            "print('hello')",
            "openai/gpt-5.6-luna",
            None,
            "",
        )

        assert result.composite == 7.0
        assert captured["model"] == "gpt-5.6-luna"
        assert captured["reasoning_effort"] == "high"
        assert captured["max_completion_tokens"] == 2048
        assert "max_tokens" not in captured
        assert captured["messages"][0]["content"] == _build_judge_system()


class TestJudgeAppWithApi:
    def test_unknown_model_provider_raises_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            judge_app_with_api("print('hello')", "unknown/model-id", None, "")
        assert "Unknown judge model provider" in str(exc_info.value)
        assert "unknown/model-id" in str(exc_info.value)

    def test_anthropic_prefix_accepted(self, monkeypatch):
        captured = {}

        class FakeAnthropicClient:
            class Messages:
                def create(self, **kwargs):
                    captured.update(kwargs)

                    class FakeContent:
                        text = json.dumps(
                            {
                                "requirement_fidelity": {
                                    "score": 7,
                                    "rationale": "Good",
                                },
                                "code_maintainability": {
                                    "score": 7,
                                    "rationale": "Clean",
                                },
                                "visual_ux_quality": {"score": 7, "rationale": "Solid"},
                                "code_robustness": {"score": 7, "rationale": "Robust"},
                            }
                        )

                    class FakeResponse:
                        content = [FakeContent()]
                        usage = None

                    return FakeResponse()

            messages = Messages()

        fake_anthropic = types.SimpleNamespace(Anthropic=lambda: FakeAnthropicClient())
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

        result = judge_app_with_api(
            "print('hello')", "anthropic/claude-sonnet-5", None, ""
        )
        assert result.composite == 7.0
        assert captured["system"] == _build_judge_system()

    def test_openai_prefix_accepted(self, monkeypatch):
        class FakeUsage:
            prompt_tokens = 100
            completion_tokens = 50

        class FakeMessage:
            content = json.dumps(
                {
                    "requirement_fidelity": {"score": 8, "rationale": "Good"},
                    "code_maintainability": {"score": 8, "rationale": "Clean"},
                    "visual_ux_quality": {"score": 8, "rationale": "Solid"},
                    "code_robustness": {"score": 8, "rationale": "Robust"},
                }
            )

        class FakeChoice:
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]
            usage = FakeUsage()

        class FakeCompletions:
            def create(self, **kwargs):
                return FakeResponse()

        class FakeChat:
            completions = FakeCompletions()

        class FakeOpenAIClient:
            def __init__(self):
                self.chat = FakeChat()

        fake_openai_module = types.SimpleNamespace(OpenAI=FakeOpenAIClient)
        monkeypatch.setitem(sys.modules, "openai", fake_openai_module)

        result = judge_app_with_api("print('hello')", "openai/gpt-4", None, "")
        assert result.composite == 8.0


class TestRetryWithBackoff:
    def test_succeeds_on_first_attempt(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = _retry_with_backoff(func, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure_then_succeeds(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("transient error")
            return "success"

        result = _retry_with_backoff(func, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("persistent error")

        with pytest.raises(RuntimeError) as exc_info:
            _retry_with_backoff(func, max_retries=3, base_delay=0.01)
        assert "persistent error" in str(exc_info.value)
        assert call_count == 3
