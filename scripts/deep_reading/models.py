"""Data models for extracted reading sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceResult:
    path: Path
    text: str
    method: str
    pages: int = 0
