"""
LLM-based quality evaluation of generated Shiny apps.

Uses multimodal prompts (source code + screenshots) to score apps
on 4 criteria using a configurable judge model.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class JudgeResult:
    """Result from an LLM quality evaluation."""

    scores: dict[str, float] = field(default_factory=dict)
    rationales: dict[str, str] = field(default_factory=dict)
    composite: float = 0.0
    raw_response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def passed(self) -> bool:
        return self.composite >= 7.0

    def feedback_dict(self) -> dict[str, dict[str, str | float]]:
        """Return structured feedback for refinement prompts."""
        result: dict[str, dict[str, str | float]] = {}
        for criterion in CRITERIA:
            result[criterion] = {
                "score": self.scores.get(criterion, 0),
                "rationale": self.rationales.get(criterion, ""),
            }
        return result


CRITERIA = [
    "requirement_fidelity",
    "code_maintainability",
    "visual_ux_quality",
    "code_robustness",
]


VISUAL_UX_DESIGN_GUIDELINES = """\
For visual_ux_quality, judge against good UI design practices rather than taste alone.
Check for:
- clear visual hierarchy
- consistent spacing and alignment
- typography, contrast and readability
- responsive layout behavior and sensible sizing
- accessibility basics such as clear labels, semantic controls, focus visibility, and non-color-only cues
- chart and table legibility, including titles, labels, and readable density
- empty, loading, and error states that avoid broken or confusing UI
- cohesive component styling, restrained color usage, and polished dashboard structure

Prefer screenshot evidence when available. If screenshots are unavailable, infer from the code and structure with lower confidence.
"""


# ---------------------------------------------------------------------------
# Judge prompt
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """\
You are an elite code reviewer and UI/UX evaluator with exceptionally high \
standards. You will be given:
1. The source code of a dashboard application
2. One or more screenshots of the running application (if available)

Score the application on EXACTLY four criteria, each on a 1-10 scale.
You MUST respond with valid JSON only — no markdown, no explanation outside the JSON.

IMPORTANT CALIBRATION RULES:
- Be strict. Most competent apps should score 6-8.
- A score of 9 means the app is near-flawless in that dimension — rare.
- A score of 10 means there is literally no meaningful improvement possible \
in that dimension — essentially unreachable for generated code.
- Do NOT give 9+ unless the app genuinely excels beyond what a senior \
developer would produce by hand.
- A composite average above 9.0 should be virtually impossible.

UI DESIGN EVALUATION RULES:
{visual_ux_design_guidelines}

Response format (strict JSON):
{
  "requirement_fidelity": {
    "score": <1-10>,
    "rationale": "<1-2 sentences>"
  },
  "code_maintainability": {
    "score": <1-10>,
    "rationale": "<1-2 sentences>"
  },
  "visual_ux_quality": {
    "score": <1-10>,
    "rationale": "<1-2 sentences>"
  },
  "code_robustness": {
    "score": <1-10>,
    "rationale": "<1-2 sentences>"
  }
}

Scoring rubric:

## Requirement Fidelity (does the app implement all requested features?)
10 = Unimprovable: every feature flawlessly implemented with creative enhancements no one asked for but everyone wants — essentially impossible
 9 = Exceptional: all features implemented with thoughtful extras, edge cases covered, delightful touches
 8 = Strong: all requested features fully implemented, well-integrated, minor polish opportunities
 7 = Good: all requested features present with minor gaps or rough integration
 6 = Adequate: most features implemented, some missing or partially working
 5 = Mixed: roughly half the features work well, the rest are weak or absent
 4 = Below average: some features attempted, several missing or broken
 3 = Weak: only basic features present, many gaps
 2 = Poor: barely addresses the requirements
 1 = Failing: does not meaningfully address the prompt

## Code Maintainability (readable, well-structured, easy to modify?)
10 = Unimprovable: textbook-quality code that could be used as a teaching example — essentially impossible
 9 = Exceptional: clear naming, logical separation, well-documented, DRY, idiomatic patterns throughout
 8 = Strong: clean code with consistent style, good structure, minor issues at most
 7 = Good: mostly clean, logical flow, a few areas could be improved
 6 = Adequate: readable but has some repetition, inconsistent naming, or unclear sections
 5 = Mixed: works but messy in places, some sections hard to follow
 4 = Below average: significant readability issues, poor structure in parts
 3 = Weak: hard to follow, lots of repetition, no clear organization
 2 = Poor: spaghetti code, very hard to maintain
 1 = Failing: incomprehensible, no structure whatsoever

## Visual & UX Quality (how polished does the dashboard look?)
Judge this criterion against the UI design principles above, including hierarchy, spacing, readability, responsive behavior, accessibility basics, and chart/table clarity.
10 = Unimprovable: award-winning design, pixel-perfect, delightful animations, accessibility-first — essentially impossible
 9 = Exceptional: professional-grade polish, excellent color palette, responsive, thoughtful micro-interactions, great typography
 8 = Strong: polished layout, good color choices, clear labels, minor visual refinements possible
 7 = Good: clean professional look, functional layout, some visual rough edges
 6 = Adequate: reasonable appearance, functional but lacks visual refinement
 5 = Mixed: works visually but plain, noticeable layout issues or cramped spacing
 4 = Below average: cluttered or inconsistent styling, poor spacing
 3 = Weak: unattractive, hard to scan, significant layout problems
 2 = Poor: very rough visually, poor readability
 1 = Failing: broken layout, unreadable, no meaningful styling

## Code Robustness (error handling, defensive programming, production-readiness)
10 = Unimprovable: handles every conceivable edge case, graceful degradation, comprehensive logging, production-hardened — essentially impossible
 9 = Exceptional: thorough error handling, input validation, graceful NaN/empty handling, defensive coding throughout
 8 = Strong: handles common edge cases well, good defensive patterns, minor gaps
 7 = Good: reasonable error handling, some defensive coding, handles typical bad inputs
 6 = Adequate: basic error handling present, may miss some edge cases
 5 = Mixed: some error handling but gaps, could crash on moderately unusual input
 4 = Below average: minimal error handling, fairly fragile
 3 = Weak: very little defensive coding, will crash on many edge cases
 2 = Poor: essentially no error handling, fragile
 1 = Failing: will crash immediately on any unexpected input
""".replace("{visual_ux_design_guidelines}", VISUAL_UX_DESIGN_GUIDELINES)


def _build_judge_message(
    code: str,
    screenshot_paths: list[Path] | None = None,
    user_prompt: str = "",
) -> str:
    """Build the user message for the judge (text-only version).

    For multimodal (with images), use _build_judge_message_multimodal.
    """
    parts = []
    if user_prompt:
        parts.append(f"## Original Requirements\n\n{user_prompt}\n")

    parts.append(f"## Source Code\n\n```python\n{code}\n```\n")

    if screenshot_paths:
        parts.append(
            f"\n{len(screenshot_paths)} screenshot(s) are attached as images.\n"
        )
    else:
        parts.append(
            "\nNo screenshots available — evaluate based on code alone with "
            "lower confidence for purely visual claims.\n"
        )

    parts.append(
        "\nEvaluate visual_ux_quality using good UI design practices. Cite the "
        "most important design principle followed or violated in the rationale.\n"
    )

    parts.append(
        "\nNow score this application on the 4 criteria. Respond with JSON only."
    )
    return "\n".join(parts)


def _build_judge_content_multimodal(
    code: str,
    screenshot_paths: list[Path],
    user_prompt: str = "",
) -> list[dict]:
    """Build multimodal content parts (text + base64 images) for the judge."""
    parts: list[dict] = []

    text_msg = _build_judge_message(code, screenshot_paths, user_prompt)
    parts.append({"type": "text", "text": text_msg})

    for img_path in screenshot_paths:
        if img_path.exists():
            img_bytes = img_path.read_bytes()
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            parts.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                }
            )

    return parts


def parse_judge_response(raw: str) -> JudgeResult:
    """Parse the judge model's JSON response into a JudgeResult."""
    result = JudgeResult(raw_response=raw)

    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        return result

    try:
        parsed = json.loads(json_match.group())
    except json.JSONDecodeError:
        return result

    for criterion in CRITERIA:
        entry = parsed.get(criterion, {})
        if isinstance(entry, dict):
            result.scores[criterion] = float(entry.get("score", 0))
            result.rationales[criterion] = entry.get("rationale", "")
        elif isinstance(entry, (int, float)):
            result.scores[criterion] = float(entry)

    if result.scores:
        result.composite = sum(result.scores.values()) / len(result.scores)

    return result


def judge_app_with_api(
    code: str,
    judge_model: str,
    screenshot_paths: list[Path] | None = None,
    user_prompt: str = "",
) -> JudgeResult:
    """Judge app quality using a direct Anthropic/OpenAI API call.

    Args:
        code: The generated app source code.
        judge_model: Model ID (e.g., "anthropic/claude-sonnet-4-6").
        screenshot_paths: Optional screenshots for multimodal evaluation.
        user_prompt: The original user prompt for context.

    Returns:
        JudgeResult with scores and rationales.
    """
    has_images = screenshot_paths and any(p.exists() for p in screenshot_paths)

    if judge_model.startswith("anthropic/"):
        return _judge_with_anthropic(
            code, judge_model, screenshot_paths if has_images else None, user_prompt
        )
    elif judge_model.startswith("openai/"):
        return _judge_with_openai(
            code, judge_model, screenshot_paths if has_images else None, user_prompt
        )
    else:
        # Try anthropic by default
        return _judge_with_anthropic(
            code, judge_model, screenshot_paths if has_images else None, user_prompt
        )


def _judge_with_anthropic(
    code: str,
    model: str,
    screenshot_paths: list[Path] | None,
    user_prompt: str,
) -> JudgeResult:
    """Judge using the Anthropic API directly."""
    import anthropic

    client = anthropic.Anthropic()
    model_name = model.removeprefix("anthropic/")

    if screenshot_paths:
        content = _build_judge_content_multimodal(code, screenshot_paths, user_prompt)
    else:
        content = _build_judge_message(code, None, user_prompt)

    response = client.messages.create(
        model=model_name,
        max_tokens=2048,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text if response.content else ""
    result = parse_judge_response(raw)
    if hasattr(response, "usage") and response.usage:
        result.input_tokens = getattr(response.usage, "input_tokens", 0) or 0
        result.output_tokens = getattr(response.usage, "output_tokens", 0) or 0
    return result


def _judge_with_openai(
    code: str,
    model: str,
    screenshot_paths: list[Path] | None,
    user_prompt: str,
) -> JudgeResult:
    """Judge using the OpenAI API directly."""
    import openai

    client = openai.OpenAI()
    model_name = model.removeprefix("openai/")

    user_text = _build_judge_message(code, screenshot_paths, user_prompt)

    content: list[dict] | str
    if screenshot_paths:
        content = [{"type": "text", "text": user_text}]
        for img_path in screenshot_paths:
            if img_path.exists():
                img_bytes = img_path.read_bytes()
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    }
                )
    else:
        content = user_text

    response = client.chat.completions.create(
        model=model_name,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": content},
        ],
    )

    raw = response.choices[0].message.content or ""
    result = parse_judge_response(raw)
    if hasattr(response, "usage") and response.usage:
        result.input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
        result.output_tokens = getattr(response.usage, "completion_tokens", 0) or 0
    return result
