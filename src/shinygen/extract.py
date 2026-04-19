"""
Extract generated app code from Inspect AI eval logs.
"""

from __future__ import annotations

import ast
import base64
import io
import json
import re
import struct
import zipfile
from pathlib import Path

from .validation import validate_framework_artifact

# Code block patterns
CODE_PATTERN_PYTHON = re.compile(r"```python\s*\n(.*?)```", re.DOTALL)
CODE_PATTERN_R = re.compile(r"```r\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
APP_ARTIFACTS = ("app.py", "app.R")
ATTACHMENT_PREFIX = "attachment://"


def _read_zip_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    """Read a ZIP member, including archives that use method 93 (zstd)."""
    try:
        return zf.read(info)
    except NotImplementedError:
        if info.compress_type != 93:
            raise

    try:
        import zstandard as zstd
    except ImportError as exc:  # pragma: no cover - exercised only when missing
        raise NotImplementedError(
            "ZIP method 93 (zstd) requires the zstandard package"
        ) from exc

    with open(zf.filename, "rb") as archive:
        archive.seek(info.header_offset)
        local_header = archive.read(30)
        (
            signature,
            _version,
            _flags,
            _compression,
            _mod_time,
            _mod_date,
            _crc,
            _compressed_size,
            _uncompressed_size,
            name_len,
            extra_len,
        ) = struct.unpack("<IHHHHHIIIHH", local_header)

        if signature != 0x04034B50:
            raise zipfile.BadZipFile("Invalid local file header")

        archive.seek(name_len + extra_len, 1)
        compressed = archive.read(info.compress_size)

    with zstd.ZstdDecompressor().stream_reader(io.BytesIO(compressed)) as reader:
        return reader.read()


def strip_line_numbers(text: str) -> str:
    """Remove line numbers from code output (e.g., from `nl -ba`)."""
    lines = []
    for line in text.split("\n"):
        m = re.match(r"^\s*\d+[→│](.*)$", line)
        if m:
            lines.append(m.group(1))
        else:
            m = re.match(r"^\s{0,5}\d{1,6}(?:\t|\s{2,})(.*)$", line)
            if m:
                lines.append(m.group(1))
            else:
                lines.append(line)
    return "\n".join(lines)


def _clean_text(text: str) -> str:
    text = strip_line_numbers(text)
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.DOTALL)
    text = re.sub(
        r"<environment_details>.*?</environment_details>", "", text, flags=re.DOTALL
    )
    return text.strip()


def _extract_heredoc_candidates(text: str, artifact_name: str) -> list[str]:
    """Extract shell heredoc bodies that write the target artifact."""
    candidates: list[str] = []
    lines = text.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]
        if artifact_name not in line or "<<" not in line:
            index += 1
            continue

        if not any(token in line for token in ("cat >", "cat >>", "tee ")):
            index += 1
            continue

        match = re.search(r"<<-?\s*['\"]?([A-Za-z0-9_]+)['\"]?", line)
        if not match:
            index += 1
            continue

        delimiter = match.group(1)
        body: list[str] = []
        index += 1
        while index < len(lines) and lines[index].strip() != delimiter:
            body.append(lines[index])
            index += 1

        if body and index < len(lines):
            candidates.append("\n".join(body).strip())

        index += 1

    return candidates


def _normalize_tool_call_arguments(raw: object) -> dict[str, object]:
    """Return tool-call arguments as a dict when possible."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"cmd": raw}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _candidate_score(code: str, artifact_name: str) -> tuple[int, int]:
    """Score how likely a code block is the target app artifact."""
    score = 0

    if artifact_name.endswith(".R"):
        if "library(shiny)" in code:
            score += 3
        if "shinyApp(" in code:
            score += 3
        if "page_sidebar" in code or "page_navbar" in code:
            score += 2
        if code.startswith("Command:") or "Output: expression(" in code:
            score -= 8
    else:
        if "from shiny" in code or "import shiny" in code:
            score += 3
        if "App(" in code or "app = App" in code:
            score += 3
        if "page_sidebar" in code or "page_navbar" in code:
            score += 2
        if "print(df.head())" in code and "App(" not in code:
            score -= 6

    return score, len(code)


def _extract_python_from_text(text: str) -> str | None:
    """Extract Python app code from text content."""
    text = _clean_text(text)
    heredoc_candidates = _extract_heredoc_candidates(text, "app.py")
    if heredoc_candidates:
        best_candidate: str | None = None
        best_score: tuple[int, int] | None = None
        for candidate in heredoc_candidates:
            try:
                ast.parse(candidate)
            except SyntaxError:
                continue
            score = _candidate_score(candidate, "app.py")
            if best_score is None or score > best_score:
                best_candidate = candidate
                best_score = score
        if best_candidate is not None:
            return best_candidate

    matches = [m.strip() for m in CODE_PATTERN_PYTHON.findall(text) if m.strip()]

    if matches:
        best_candidate: str | None = None
        best_score: tuple[int, int] | None = None
        for candidate in sorted(matches, key=len, reverse=True):
            try:
                ast.parse(candidate)
                score = _candidate_score(candidate, "app.py")
                if best_score is None or score > best_score:
                    best_candidate = candidate
                    best_score = score
            except SyntaxError:
                continue
        if best_candidate and best_score and best_score[0] >= 3:
            return best_candidate

    # Fallback: look for raw Python starting from first import
    app_markers = ("from shiny", "import shiny", "page_sidebar", "App(", "app = App")
    if not any(marker in text for marker in app_markers):
        return None

    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("from ", "import ", "#")):
            start = i
            break
    if start is None:
        return None

    candidate = "\n".join(lines[start:]).strip()
    try:
        ast.parse(candidate)
        score = _candidate_score(candidate, "app.py")
        return candidate if len(candidate) > 100 and score[0] >= 3 else None
    except SyntaxError:
        return None


def _extract_r_from_text(text: str) -> str | None:
    """Extract R app code from text content."""
    text = _clean_text(text)
    heredoc_candidates = _extract_heredoc_candidates(text, "app.R")
    if heredoc_candidates:
        return max(heredoc_candidates, key=lambda x: _candidate_score(x, "app.R"))

    matches = [m.strip() for m in CODE_PATTERN_R.findall(text) if m.strip()]

    if matches:
        return max(matches, key=lambda x: _candidate_score(x, "app.R"))

    if text.startswith("Command:") or "Output: expression(" in text:
        return None
    if "library(shiny)" not in text and "shinyApp(" not in text:
        return None

    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("#", "library(", "ui <-", "app_ui <-", "server <-")):
            start = i
            break
    if start is None:
        return None

    candidate = "\n".join(lines[start:]).strip()
    score = _candidate_score(candidate, "app.R")
    return candidate if len(candidate.splitlines()) >= 4 and score[0] >= 3 else None


def find_app_code_in_text(text: str, artifact_name: str) -> str | None:
    """Extract app code from a text string."""
    if artifact_name.endswith(".R"):
        return _extract_r_from_text(text)
    return _extract_python_from_text(text)


def find_app_code_in_messages(
    messages: list[dict],
    artifact_name: str = "app.py",
) -> str | None:
    """Search eval log messages for the final artifact content.

    Strategies:
    1. File-write tool calls containing the artifact name.
    2. Code blocks in assistant text.
    3. Tool output messages (codex CLI terminal output).
    """
    candidates: list[str] = []

    # Strategy 1: file-write tool calls (latest first)
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", [])
        if isinstance(content, str):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            tool_name = part.get("name", "") or part.get("tool", "")
            tool_input = part.get("input", {})
            if isinstance(tool_input, dict):
                if "file" in tool_name.lower() or "write" in tool_name.lower():
                    path_val = tool_input.get("file_path", tool_input.get("path", ""))
                    if artifact_name in str(path_val):
                        code = tool_input.get(
                            "content", tool_input.get("file_text", "")
                        )
                        if code:
                            candidates.append(code)

        for tool_call in msg.get("tool_calls", []) or []:
            if not isinstance(tool_call, dict):
                continue
            arguments = _normalize_tool_call_arguments(tool_call.get("arguments", {}))
            for value in arguments.values():
                if not isinstance(value, str):
                    continue
                code = find_app_code_in_text(value, artifact_name)
                if code:
                    candidates.append(code)

    # Strategy 2: assistant text content
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = [
                p.get("text", "")
                for p in content
                if isinstance(p, dict) and "text" in p
            ]
            content = "\n".join(text_parts)
        code = find_app_code_in_text(content, artifact_name)
        if code:
            candidates.append(code)

    if candidates:
        return max(candidates, key=lambda x: _candidate_score(x, artifact_name))

    return None


def _decode_image_attachment(attachment: object) -> bytes | None:
    """Decode an Inspect image attachment payload if it is base64 data."""
    if isinstance(attachment, dict):
        for key in ("data", "content", "bytes"):
            if key in attachment:
                attachment = attachment[key]
                break

    if not isinstance(attachment, str) or not attachment.startswith("data:"):
        return None

    _header, separator, payload = attachment.partition(",")
    if not separator:
        return None

    try:
        return base64.b64decode(payload)
    except (ValueError, TypeError):
        return None


def extract_last_image_attachment(log_path: Path, output_path: Path) -> Path | None:
    """Write the last image attachment in an Inspect eval log to disk."""
    last_image: bytes | None = None

    with zipfile.ZipFile(log_path) as z:
        sample_files = sorted(
            n for n in z.namelist() if n.startswith("samples/") and n.endswith(".json")
        )

        for sample_file in sample_files:
            sample = json.loads(_read_zip_member(z, z.getinfo(sample_file)))
            attachments = sample.get("attachments") or {}
            messages = sample.get("messages") or []

            for msg in messages:
                content = msg.get("content")
                if not isinstance(content, list):
                    continue

                for part in content:
                    if not isinstance(part, dict) or part.get("type") != "image":
                        continue

                    image_ref = part.get("image")
                    if not isinstance(image_ref, str):
                        continue

                    attachment_id = image_ref.removeprefix(ATTACHMENT_PREFIX)
                    decoded = _decode_image_attachment(attachments.get(attachment_id))
                    if decoded:
                        last_image = decoded

    if last_image is None:
        return None

    output_path.write_bytes(last_image)
    return output_path


def extract_from_log(log_path: Path) -> dict[str, str]:
    """Extract app code from an Inspect AI .eval log file.

    Args:
        log_path: Path to the .eval ZIP file.

    Returns:
        Dict of {sample_id: code_string}.
    """
    code_results: dict[str, str] = {}

    with zipfile.ZipFile(log_path) as z:
        sample_files = [
            n for n in z.namelist() if n.startswith("samples/") and n.endswith(".json")
        ]

        for sf in sorted(sample_files):
            sample = json.loads(_read_zip_member(z, z.getinfo(sf)))
            sid = sample.get("id", sf)
            messages = sample.get("messages", [])

            metadata = sample.get("metadata", {})
            artifact = metadata.get("primary_artifact", "app.py")
            framework = metadata.get(
                "framework",
                "shiny_r" if artifact.endswith(".R") else "shiny_python",
            )

            code = find_app_code_in_messages(messages, artifact)
            if code:
                valid, _reason = validate_framework_artifact(framework, artifact, code)
                if valid:
                    code_results[sid] = code

    return code_results
