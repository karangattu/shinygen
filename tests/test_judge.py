"""Tests for shinygen.judge"""

import json

from shinygen.judge import CRITERIA, JudgeResult, parse_judge_response


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
