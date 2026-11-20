"""Prospective XP boundary validation (never retrofits historical enforcement)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import TypedDict


class Founder(TypedDict):
    id: int
    x: int
    y: int
    label: int
    sequence_hex: str


class Case(TypedDict):
    index: int
    count: int
    mixed: bool
    seed: int
    repeat: int
    observed: int
    founders: list[Founder]
    config: str
    config_sha256: str
    environment: dict[str, str]


class Snapshot(TypedDict):
    tick: int
    event: str
    total: int
    host: int


def require(condition: bool, message: str = 'XP validation failed') -> None:
    # AssertionError preserves the old reader interface, but is never optimized out.
    if not condition:
        raise AssertionError(message)


def allocated(root: Path) -> int:
    """Conservative logical/allocated accounting; never traverse symlinks.

    Hard links are counted per path. Non-regular nodes count their allocation;
    symlink targets (including directories outside the budget) are not followed.
    """
    info = root.lstat()
    total = max(info.st_size, info.st_blocks * 512)
    if stat.S_ISDIR(info.st_mode):
        with os.scandir(root) as entries:
            for entry in entries:
                total += allocated(Path(entry.path))
    return total


def object_from(path: Path) -> dict[str, object]:
    value: object = json.loads(path.read_text())
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ValueError(f'expected JSON object: {path}')
    return value


def authorization(integrity: bool, canonical: bool) -> bool:
    """Integrity cannot substitute for the required biological positive control."""
    return integrity and canonical
