"""Compatibility inventory for scan tools; book data lives in source/book.yml."""

from pathlib import Path
from typing import Any

import yaml

BOOK: dict[str, Any] = yaml.safe_load(
    (Path(__file__).resolve().parents[1] / "source/book.yml").read_text(
        encoding="utf-8"
    )
)
PIECES: list[dict[str, Any]] = [piece for piece in BOOK["pieces"] if piece["original"]]


def by_id(pid: str) -> dict[str, Any]:
    for piece in PIECES:
        if piece["id"] == pid:
            return piece
    raise KeyError(pid)
