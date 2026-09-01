"""
Skill file loading and injection into Docker sandbox.
"""

from __future__ import annotations

import logging
import os
import shutil
import tarfile
import tempfile
from functools import lru_cache
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from urllib.request import Request, urlopen

from inspect_ai.tool import Skill, read_skills

from .config import FRAMEWORKS, PACKAGE_DIR

# Bundled skills (visual QA). Framework skills (Shiny for Python and Shiny for R)
# are downloaded from their respective upstream repos by _default_skill_dir().
BUNDLED_SKILLS_DIR = PACKAGE_DIR / "skills"

PY_SHINY_SKILL_REF = "main"
PY_SHINY_SKILL_ARCHIVE_URL = (
    "https://codeload.github.com/posit-dev/py-shiny/tar.gz/{ref}"
)
PY_SHINY_SKILL_REPO_PATH = PurePosixPath("shiny/.agents/skills/shiny-for-python")

R_SHINY_SKILL_REF = "main"
R_SHINY_SKILL_ARCHIVE_URL = "https://codeload.github.com/rstudio/shiny/tar.gz/{ref}"
R_SHINY_SKILL_REPO_PATH = PurePosixPath("inst/skills/shiny-for-r")

logger = logging.getLogger(__name__)


def _skills_cache_dir() -> Path:
    configured = os.environ.get("SHINYGEN_SKILLS_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()

    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    cache_home = Path(xdg_cache).expanduser() if xdg_cache else Path.home() / ".cache"
    return cache_home / "shinygen" / "skills"


def _fetch_github_skill(
    skill_name: str,
    repo_slug: str,
    ref: str,
    archive_url: str,
    repo_path: PurePosixPath,
    cache_dir: str,
) -> Path:
    cache_key = quote(ref, safe="").replace("%", "_")
    target = Path(cache_dir) / repo_slug / cache_key / skill_name
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{skill_name}-skill-", dir=target.parent
        ) as temp_dir:
            staged = Path(temp_dir) / skill_name
            request = Request(archive_url, headers={"User-Agent": "shinygen"})
            with urlopen(request, timeout=30) as response:
                with tarfile.open(fileobj=response, mode="r|gz") as archive:
                    for member in archive:
                        parts = PurePosixPath(member.name).parts
                        if len(parts) < 2:
                            continue
                        try:
                            relative = PurePosixPath(*parts[1:]).relative_to(repo_path)
                        except ValueError:
                            continue
                        if ".." in relative.parts:
                            raise ValueError(
                                f"unsafe path in {repo_slug} archive: {member.name}"
                            )

                        destination = staged.joinpath(*relative.parts)
                        if member.isdir():
                            destination.mkdir(parents=True, exist_ok=True)
                        elif member.isfile():
                            source = archive.extractfile(member)
                            if source is None:
                                continue
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            with destination.open("wb") as output:
                                shutil.copyfileobj(source, output)

            if not (staged / "SKILL.md").is_file():
                raise ValueError(f"archive does not contain {repo_path}/SKILL.md")

            if target.exists():
                shutil.rmtree(target)
            staged.rename(target)
    except (OSError, tarfile.TarError, ValueError) as exc:
        if (target / "SKILL.md").is_file():
            logger.warning(
                "Could not refresh the %s skill from %s; using cached copy: %s",
                skill_name,
                archive_url,
                exc,
            )
            return target
        raise RuntimeError(
            f"Could not download the {skill_name} skill from {archive_url}"
        ) from exc

    return target


@lru_cache
def _fetch_py_shiny_skill(ref: str, archive_url: str, cache_dir: str) -> Path:
    return _fetch_github_skill(
        skill_name="shiny-for-python",
        repo_slug="py-shiny",
        ref=ref,
        archive_url=archive_url,
        repo_path=PY_SHINY_SKILL_REPO_PATH,
        cache_dir=cache_dir,
    )


@lru_cache
def _fetch_r_shiny_skill(ref: str, archive_url: str, cache_dir: str) -> Path:
    return _fetch_github_skill(
        skill_name="shiny-for-r",
        repo_slug="shiny",
        ref=ref,
        archive_url=archive_url,
        repo_path=R_SHINY_SKILL_REPO_PATH,
        cache_dir=cache_dir,
    )


def _default_skill_dir(framework_key: str) -> Path:
    if framework_key == "shiny_python":
        ref = os.environ.get("SHINYGEN_PY_SHINY_SKILL_REF", PY_SHINY_SKILL_REF)
        archive_url = os.environ.get(
            "SHINYGEN_PY_SHINY_SKILL_ARCHIVE_URL",
            PY_SHINY_SKILL_ARCHIVE_URL.format(ref=quote(ref, safe="")),
        )
        return _fetch_py_shiny_skill(ref, archive_url, str(_skills_cache_dir()))

    if framework_key == "shiny_r":
        ref = (
            os.environ.get("SHINYGEN_R_SHINY_SKILL_REF")
            or os.environ.get("SHINYGEN_SHINY_R_SKILL_REF")
            or R_SHINY_SKILL_REF
        )
        archive_url = (
            os.environ.get("SHINYGEN_R_SHINY_SKILL_ARCHIVE_URL")
            or os.environ.get("SHINYGEN_SHINY_R_SKILL_ARCHIVE_URL")
            or R_SHINY_SKILL_ARCHIVE_URL.format(ref=quote(ref, safe=""))
        )
        return _fetch_r_shiny_skill(ref, archive_url, str(_skills_cache_dir()))

    fw = FRAMEWORKS[framework_key]
    return BUNDLED_SKILLS_DIR / fw["skill_dir"]


def load_skill_files(
    skill_dir: Path,
) -> list[Skill]:
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
) -> list[Skill]:
    """Load the default skill for a framework.

    Args:
        framework_key: "shiny_python" or "shiny_r"

    Returns:
        Parsed skills ready to install with the agent's native skill loader.
    """
    skill_dir = _default_skill_dir(framework_key)

    if not skill_dir.exists():
        return []

    return load_skill_files(skill_dir)


def load_skill_context_text(
    framework_key: str,
    *,
    include_references: bool = True,
) -> str:
    """Load framework skills as a single text block for prompt injection.

    Used when appending skills directly to the system prompt
    (alternative to file-based injection).

    Args:
        framework_key: "shiny_python" or "shiny_r"

    Returns:
        Concatenated skill text.
    """
    fw = FRAMEWORKS[framework_key]
    skill_dir = _default_skill_dir(framework_key)

    parts: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        label = fw["label"]
        parts.append(f"# Skill: {label} Dashboard\n\n" + skill_md.read_text())

    refs_dir = skill_dir / "references"
    if include_references and refs_dir.exists():
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


def collect_skill_sample_files(
    framework_key: str,
    target_root: str = ".agents/skills",
    include_visual_qa: bool = False,
) -> dict[str, str]:
    """Collect framework skill files for staging via Inspect AI Sample.files.

    Used to guarantee Codex CLI discovers the skill at its documented
    location (`<cwd>/.agents/skills/<skill-name>/...`). inspect_swe's
    codex_cli solver writes skills under `$CODEX_HOME/skills`, which is
    not one of Codex's documented scan paths.

    Args:
        framework_key: "shiny_python" or "shiny_r".
        target_root: Sandbox path (relative to cwd) under which each skill
            will be placed in its own subdirectory.
        include_visual_qa: When True, also stage the visual-qa skill.

    Returns:
        Mapping of sandbox-relative file paths to file contents.
    """
    skill_dirs: list[Path] = []
    primary = _default_skill_dir(framework_key)
    if primary.exists():
        skill_dirs.append(primary)
    if include_visual_qa and VISUAL_QA_SKILL_DIR.exists():
        skill_dirs.append(VISUAL_QA_SKILL_DIR)

    out: dict[str, str] = {}
    for skill_dir in skill_dirs:
        skill_name = skill_dir.name
        for path in skill_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.name == ".DS_Store":
                continue
            rel = path.relative_to(skill_dir).as_posix()
            sandbox_rel = f"{target_root}/{skill_name}/{rel}"
            try:
                out[sandbox_rel] = path.read_text()
            except UnicodeDecodeError:
                # Skip binary assets we cannot stage as text.
                continue
    return out
