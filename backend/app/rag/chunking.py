"""Split one page of text into chunks. A chunk never spans two pages, so a page citation is exact."""
from __future__ import annotations

import re
from typing import List

_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def normalise(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_page(text: str, target: int = 900, overlap: int = 120) -> List[str]:
    """Greedy sentence packing up to ~`target` characters, carrying the tail of the previous chunk as overlap."""
    text = normalise(text)
    if not text:
        return []
    if len(text) <= target:
        return [text]
    sentences = [s.strip() for s in _SENTENCE.split(text) if s.strip()]
    chunks: List[str] = []
    current = ""
    for s in sentences:
        # A single very long "sentence" (no punctuation) is hard-split.
        while len(s) > target:
            head, s = s[:target], s[target:]
            if current:
                chunks.append(current)
                current = ""
            chunks.append(head)
        if current and len(current) + 1 + len(s) > target:
            chunks.append(current)
            tail = current[-overlap:]
            tail = tail[tail.find(" ") + 1:] if " " in tail else tail
            current = f"{tail} {s}".strip()
        else:
            current = f"{current} {s}".strip()
    if current:
        chunks.append(current)
    return chunks
