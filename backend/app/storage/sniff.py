"""Identify a file from its leading bytes instead of trusting the client's Content-Type header."""
from __future__ import annotations

from typing import Optional


def sniff_content_type(data: bytes) -> Optional[str]:
    head = data[:16]
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if head[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\x1a\x45\xdf\xa3"):  # EBML header (WebM/Matroska)
        return "audio/webm"
    if head.startswith(b"OggS"):
        return "audio/ogg"
    if data[4:8] == b"ftyp":  # ISO base media (m4a/mp4)
        return "audio/mp4"
    if head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return "audio/mpeg"
    return None
