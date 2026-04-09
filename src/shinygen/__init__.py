"""
shinygen — Generate Shiny apps with LLMs.
"""

from __future__ import annotations

from .api import BatchJob, BatchResult, GenerationResult, batch, generate
from .config import APIKeyMissingError, DockerNotAvailableError
from .pricing import UsageStats

__version__ = "0.1.0"

__all__ = [
    "generate",
    "batch",
    "GenerationResult",
    "BatchJob",
    "BatchResult",
    "UsageStats",
    "DockerNotAvailableError",
    "APIKeyMissingError",
    "__version__",
]
