"""Tests for shinygen.judge"""

import json
import sys
import types

import pytest

from shinygen.judge import (
    CRITERIA,
    JUDGE_SYSTEM,
    JudgeResult,
    _build_judge_message,
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
    def test_visual_ux_rubric_requires_design_best_practices(self):
        for phrase in [
            "visual hierarchy",
            "spacing and alignment",
            "typography",
            "contrast and readability",
            "responsive",
            "accessibility basics",
            "chart and table legibility",
            "empty, loading, and error states",
        ]:
            assert phrase in JUDGE_SYSTEM

    def test_judge_message_requests_design_principle_based_evaluation(self):
        message = _build_judge_message("print('hello')")

        assert "good UI design practices" in message
        assert "design principle" in message
        assert "lower confidence" in message

    def test_visual_ux_rubric_is_calibrated_to_human_dashboard_preferences(self):
        for phrase in [
            "human-perceived visual quality",
            "one-screen usefulness",
            "conventional Shiny",
            "prominent primary visualization",
            "Clean alone is not enough",
            "stuck loading indicators",
        ]:
            assert phrase in JUDGE_SYSTEM


class TestOpenAIJudgeRequest:
    def test_gpt5_uses_max_completion_tokens(self, monkeypatch):
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
            "openai/gpt-5.4-mini-2026-03-17",
            None,
            "",
        )

        assert result.composite == 7.0
        assert captured["model"] == "gpt-5.4-mini-2026-03-17"
        assert captured["max_completion_tokens"] == 2048
        assert "max_tokens" not in captured


class TestJudgeAppWithApi:
    def test_unknown_model_provider_raises_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            judge_app_with_api("print('hello')", "unknown/model-id", None, "")
        assert "Unknown judge model provider" in str(exc_info.value)
        assert "unknown/model-id" in str(exc_info.value)

    def test_anthropic_prefix_accepted(self, monkeypatch):
        class FakeAnthropicClient:
            class Messages:
                def create(self, **kwargs):
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
