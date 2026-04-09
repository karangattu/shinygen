"""
Skill file loading and injection into Docker sandbox.
"""

from __future__ import annotations

from pathlib import Path

from .config import AGENT_SKILLS_DIR, FRAMEWORKS, PACKAGE_DIR

# Default bundled skills
BUNDLED_SKILLS_DIR = PACKAGE_DIR / "skills"


def load_skill_files(
    skill_dir: Path,
    agent: str,
) -> dict[str, str]:
    """Load skill files from a directory, mapped to agent-appropriate paths.

    The skill directory should contain a SKILL.md and optionally a
    references/ subdirectory with additional markdown files.

    Args:
        skill_dir: Path to the skill directory on the host.
        agent: Agent name ("claude_code" or "codex_cli").

    Returns:
        Dict of {sandbox_relative_path: file_content} suitable for
        merging into an Inspect AI Sample's files dict.
    """
    target_prefix = AGENT_SKILLS_DIR[agent]
    files: dict[str, str] = {}

    skill_name = skill_dir.name

    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        files[f"{target_prefix}/{skill_name}/SKILL.md"] = skill_md.read_text()

    refs_dir = skill_dir / "references"
    if refs_dir.exists():
        for ref in sorted(refs_dir.glob("*.md")):
            files[f"{target_prefix}/{skill_name}/references/{ref.name}"] = ref.read_text()

    return files


def load_default_skills(
    framework_key: str,
    agent: str,
) -> dict[str, str]:
    """Load the bundled default skills for a framework.

    Args:
        framework_key: "shiny_python" or "shiny_r"
        agent: Agent name ("claude_code" or "codex_cli").

    Returns:
        Dict of {sandbox_relative_path: file_content}.
    """
    fw = FRAMEWORKS[framework_key]
    skill_dir_name = fw["skill_dir"]
    skill_dir = BUNDLED_SKILLS_DIR / skill_dir_name

    if not skill_dir.exists():
        return {}

    return load_skill_files(skill_dir, agent)


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


def load_visual_qa_skills(agent: str) -> dict[str, str]:
    """Load the visual self-evaluation skill files.

    Args:
        agent: Agent name ("claude_code" or "codex_cli").

    Returns:
        Dict of {sandbox_relative_path: file_content}.
    """
    if not VISUAL_QA_SKILL_DIR.exists():
        return {}
    return load_skill_files(VISUAL_QA_SKILL_DIR, agent)
