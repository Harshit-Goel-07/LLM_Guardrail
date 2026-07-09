"""Jailbreak corpus loader.

The corpus is a JSONL file of known attack prompts, each labelled with a category.
It powers the semantic-similarity layer: an incoming prompt that is close (in
embedding space) to a known attack is suspicious even if no regex fires.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .schemas import Category


@dataclass(frozen=True)
class CorpusEntry:
    corpus_id: str
    text: str
    category: Category


def load_corpus(path: Path) -> list[CorpusEntry]:
    """Load labelled attack prompts from a JSONL file.

    Each line: {"id": "...", "text": "...", "category": "jailbreak"}
    Lines that are blank or start with ``#`` are ignored.
    """
    if not path.exists():
        raise FileNotFoundError(f"Jailbreak corpus not found at {path}")

    entries: list[CorpusEntry] = []
    with path.open("r", encoding="utf-8") as fh:
        for i, raw in enumerate(fh):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            obj = json.loads(line)
            entries.append(
                CorpusEntry(
                    corpus_id=str(obj.get("id", f"C{i:04d}")),
                    text=obj["text"],
                    category=Category(obj.get("category", "jailbreak")),
                )
            )
    if not entries:
        raise ValueError(f"Jailbreak corpus at {path} contained no entries")
    return entries
