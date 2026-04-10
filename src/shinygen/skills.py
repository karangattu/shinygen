"""
Skill file loading and injection into Docker sandbox.
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai.tool import Skill, read_skills

from .config import FRAMEWORKS, PACKAGE_DIR

# Default bundled skills
BUNDLED_SKILLS_DIR = PACKAGE_DIR / "skills"


def load_skill_files(
    skill_dir: Path,
)-> list[Skill]:
    """Load agent skills from a skill directory.

    The skill directory must contain a valid SKILL.md and may also contain
    scripts/, references/, and assets/ subdirectories.

    Args:
        skill_dir: Path to the skill directory on the host.

    Returns:
        Parsed skills ready to install with the agent's native skill loader.
    """
    if not skill_dir.exists():
        return []

    return read_skills([skill_dir])


def load_default_skills(
    framework_key: str,
)-> list[Skill]:
    """Load the bundled default skills for a framework.

    Args:
        framework_key: "shiny_python" or "shiny_r"

    Returns:
        Parsed skills ready to install with the agent's native skill loader.
    """
    fw = FRAMEWORKS[framework_key]
    skill_dir_name = fw["skill_dir"]
    skill_dir = BUNDLED_SKILLS_DIR / skill_dir_name

    if not skill_dir.exists():
        return []

    return load_skill_files(skill_dir)


def load_skill_context_text(
    framework_key: str,
) -> str:
    """Load bundled skills as a single text block for prompt injection.

    Used when appending skills directly to the system prompt
    (alternative to file-based injection).

    Args:
        framework_key: "shiny_python" or "shiny_r"

    Returns:
        Concatenated skill text.
    """
    fw = FRAMEWORKS[framework_key]
    skill_dir = BUNDLED_SKILLS_DIR / fw["skill_dir"]

    parts: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        label = fw["label"]
        parts.append(f"# Skill: {label} Dashboard\n\n" + skill_md.read_text())

    refs_dir = skill_dir / "references"
    if refs_dir.exists():
        for ref in sorted(refs_dir.glob("*.md")):
            parts.append(f"\n\n# Reference: {ref.stem}\n\n" + ref.read_text())

    return "\n".join(parts)


# Directory containing visual QA skill
VISUAL_QA_SKILL_DIR = BUNDLED_SKILLS_DIR / "visual-qa"


def load_visual_qa_skills() -> list[Skill]:
    """Load the visual self-evaluation skill files.

    Returns:
        Parsed skills ready to install with the agent's native skill loader.
    """
    if not VISUAL_QA_SKILL_DIR.exists():
        return []
    return load_skill_files(VISUAL_QA_SKILL_DIR)
