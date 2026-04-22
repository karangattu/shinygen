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
    """Result from an LLM quality evaluation.

    When the result is produced by averaging across multiple judges,
    ``per_judge`` holds one entry per contributing judge and
    ``judge_models`` lists the model IDs in the order they were called.
    For single-judge runs both fields stay empty so the surface stays
    backwards compatible.
    """

    scores: dict[str, float] = field(default_factory=dict)
    rationales: dict[str, str] = field(default_factory=dict)
    composite: float = 0.0
    raw_response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    judge_models: list[str] = field(default_factory=list)
    per_judge: list[dict] = field(default_factory=list)

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
For visual_ux_quality, judge the dashboard against MODERN professional UI \
standards (think Vercel, Linear, Stripe, Notion, Observable, modern BI tools). \
Be ruthlessly strict — most Shiny defaults are NOT modern and should score 5-6, \
not 7+. Holding a high bar here is the explicit goal of this benchmark.

Core design principles to evaluate: visual hierarchy, spacing and alignment, \
typography, contrast and readability, responsive layout behavior, \
accessibility basics, chart and table legibility, and empty, loading, and \
error states. Absence of several of these is evidence of a sub-7 score.

Layout & structure
- intentional grid with generous, consistent spacing (not cramped "bslib default" look)
- clear visual hierarchy: primary KPIs prominent, secondary info subordinated
- sensible information density — neither empty nor crowded
- responsive behavior: content reflows, no horizontal scroll at common widths
- deliberate use of cards / sections with consistent radius, border, and elevation

Typography & color
- a refined type scale (distinct sizes/weights for title, section, body, caption)
- readable line-height and measure; no walls of default 14px text
- restrained, intentional color palette (2-4 accent colors max, semantic usage)
- sufficient contrast for text, icons, and chart elements (WCAG AA or better)
- dark-mode friendliness or coherent light theme — not the grey Shiny default

Components & interactions
- inputs grouped logically with clear labels and helper text where useful
- buttons/links styled consistently with clear hover / focus / disabled states
- value boxes / KPI tiles have meaningful iconography, units, and deltas — not \
just a bare number
- tables have zebra/hover rows, aligned numerics, readable column widths, and \
sensible pagination
- charts have titles, axis labels, units, legible legends, and restrained color \
(no default plotly rainbow, no raw matplotlib axes unless styled)

States & polish
- empty, loading, and error states handled gracefully (no raw tracebacks, no \
stuck spinners, no blank panels)
- filters/controls produce visible, responsive feedback
- no overlapping elements, clipped labels, or broken layouts at the screenshot \
viewport
- accessibility basics: semantic controls, keyboard focus visibility, \
non-color-only cues, descriptive labels

Calibration for visual_ux_quality specifically:
- Default bslib / shinydashboard / fluidPage with minor tweaks = 5
- Reasonable bslib page_sidebar with value_boxes and plotly defaults = 6
- Thoughtful layout + restrained palette + labeled charts + polished tables = 7
- Add modern typography, coherent spacing system, styled KPI tiles, refined \
chart styling = 8
- Production-grade look indistinguishable from a hand-crafted modern BI tool = 9
- 10 is essentially unreachable.

Deduct aggressively for: cramped spacing, default Shiny look, unlabeled or \
rainbow charts, raw numeric tables, clashing colors, broken responsive \
behavior, missing empty/error states, or any visible layout bug in the \
screenshots.

Prefer screenshot evidence when available. If screenshots are unavailable, \
infer from the code and structure with LOWER confidence and cap \
visual_ux_quality at 7 unless the code unambiguously demonstrates modern \
styling (custom CSS, design tokens, deliberate theme configuration, etc.).
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
Judge this criterion against the MODERN UI design principles above. Be \
strict: default Shiny/bslib output is NOT modern and should not clear 6. Use \
screenshot evidence as the primary signal.
10 = Unimprovable: award-winning design, pixel-perfect, delightful animations, accessibility-first — essentially impossible
 9 = Exceptional: production-grade polish indistinguishable from a hand-crafted modern BI tool; refined typography, coherent spacing system, styled KPI tiles, deliberate color palette, responsive, thoughtful micro-interactions
 8 = Strong: modern look with polished layout, custom styling beyond defaults, restrained palette, well-labeled charts, tables with aligned numerics and readable density
 7 = Good: clean professional look going noticeably beyond Shiny defaults — thoughtful layout, restrained palette, labeled charts, polished tables; a few rough edges remain
 6 = Adequate: sensible bslib layout with value_boxes and default plotly charts; functional but plain, unmistakably "Shiny default" styling
 5 = Mixed: default fluidPage or shinydashboard with minor tweaks; noticeable spacing issues, unlabeled charts, or inconsistent component styling
 4 = Below average: cluttered or inconsistent styling, poor spacing, rainbow/default chart colors, cramped tables
 3 = Weak: unattractive, hard to scan, significant layout problems, obvious visual bugs in screenshots
 2 = Poor: very rough visually, poor readability, clashing colors, broken responsive behavior
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
        count = len(screenshot_paths)
        if count == 1:
            parts.append(
                "\n1 screenshot is attached as an image (the rendered app).\n"
            )
        else:
            # Name each screenshot so the judge can correlate the image with
            # its tab/view label. Multi-tab dashboards used to be scored
            # against the landing image only, biasing visual_ux_quality
            # downward — give the judge the full set and tell it to evaluate
            # the app holistically.
            labelled = "\n".join(
                f"  {idx}. `{path.name}`"
                for idx, path in enumerate(screenshot_paths, start=1)
            )
            parts.append(
                f"\n{count} screenshots are attached, in DOM order across the app's "
                "tabs / nav-panels:\n\n"
                f"{labelled}\n\n"
                "**Judge the app as a whole, not one screenshot.** "
                "The first image is the landing view; subsequent images are the "
                "remaining tabs/views. Score `visual_ux_quality` against the "
                "*combined* set: a polished landing page with broken or near-empty "
                "tabs is worse than a uniformly polished multi-tab app, and a "
                "dashboard whose secondary tabs are as carefully designed as the "
                "landing page deserves credit for that breadth. Likewise, score "
                "`requirement_fidelity` against features visible across all tabs, "
                "not only the first one.\n"
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


def judge_app_with_models(
    code: str,
    judge_models: list[str],
    screenshot_paths: list[Path] | None = None,
    user_prompt: str = "",
) -> JudgeResult:
    """Judge app quality using one or more judge models and merge results.

    Each judge in ``judge_models`` is called independently. Their per-criterion
    scores are averaged into the merged ``scores`` and ``composite``. Rationales
    are concatenated with a model-name prefix so refinement prompts surface
    every judge's reasoning. Token counts are summed across judges.

    Failures from individual judges are recorded under ``per_judge`` with an
    ``error`` field but do not abort the run as long as at least one judge
    returns a parseable response. If every judge fails, the returned
    ``JudgeResult`` has empty scores and ``composite == 0`` (matching the
    single-judge failure surface so callers can keep their existing handling).

    Args:
        code: The generated app source code.
        judge_models: One or more resolved model IDs
            (e.g. ``["anthropic/claude-sonnet-4-6", "openai/gpt-5.4-mini-..."]``).
        screenshot_paths: Optional screenshots for multimodal evaluation.
        user_prompt: The original user prompt for context.

    Returns:
        A merged ``JudgeResult`` with averaged scores and per-judge details.
    """
    if not judge_models:
        raise ValueError("judge_models must contain at least one model ID")

    merged = JudgeResult(judge_models=list(judge_models))
    per_criterion_scores: dict[str, list[float]] = {c: [] for c in CRITERIA}
    per_criterion_rationales: dict[str, list[str]] = {c: [] for c in CRITERIA}

    for model_id in judge_models:
        try:
            single = judge_app_with_api(
                code, model_id, screenshot_paths, user_prompt
            )
            merged.input_tokens += single.input_tokens
            merged.output_tokens += single.output_tokens
            merged.per_judge.append(
                {
                    "model": model_id,
                    "composite": single.composite,
                    "scores": dict(single.scores),
                    "rationales": dict(single.rationales),
                    "input_tokens": single.input_tokens,
                    "output_tokens": single.output_tokens,
                }
            )
            for criterion in CRITERIA:
                if criterion in single.scores:
                    per_criterion_scores[criterion].append(
                        float(single.scores[criterion])
                    )
                rationale = single.rationales.get(criterion, "").strip()
                if rationale:
                    per_criterion_rationales[criterion].append(
                        f"[{model_id}] {rationale}"
                    )
        except Exception as exc:  # pragma: no cover - defensive
            merged.per_judge.append({"model": model_id, "error": str(exc)})

    for criterion, values in per_criterion_scores.items():
        if values:
            merged.scores[criterion] = sum(values) / len(values)
    for criterion, rationales in per_criterion_rationales.items():
        if rationales:
            merged.rationales[criterion] = "\n\n".join(rationales)

    if merged.scores:
        merged.composite = sum(merged.scores.values()) / len(merged.scores)

    return merged


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
    token_limit_arg = (
        {"max_completion_tokens": 2048}
        if model_name.startswith("gpt-5")
        else {"max_tokens": 2048}
    )

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
        **token_limit_arg,
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
