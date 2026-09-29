"""Text cleaning and chunking for the knowledge-base ingestion pipeline."""

import re

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
EXCESS_BLANK_LINES = re.compile(r"\n{3,}")
TRAILING_SPACES = re.compile(r"[ \t]+\n")
HEADING = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    text = CONTROL_CHARS.sub("", text)
    text = TRAILING_SPACES.sub("\n", text)
    text = EXCESS_BLANK_LINES.sub("\n\n", text)
    return text.strip()


def extract_title(text: str, fallback: str) -> str:
    match = HEADING.search(text)
    return match.group(1).strip()[:255] if match else fallback[:255]


def split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into ~chunk_size character chunks, preferring paragraph boundaries.

    Consecutive chunks share roughly `overlap` characters so an answer spanning a boundary
    is still retrievable from either side.
    """
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    pieces: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            pieces.append(paragraph)
        else:
            pieces.extend(_split_long_paragraph(paragraph, chunk_size, overlap))

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            # Start the overlap at a word boundary to avoid half words.
            if " " in tail:
                tail = tail[tail.index(" ") + 1 :]
            current = f"{tail}\n\n{piece}" if tail and len(tail) + len(piece) + 2 <= chunk_size else piece
        else:
            current = piece
    if current:
        chunks.append(current)
    return chunks


def _split_long_paragraph(paragraph: str, chunk_size: int, overlap: int) -> list[str]:
    """Word-boundary sliding window for paragraphs longer than one chunk."""
    words = paragraph.split()
    windows: list[str] = []
    start = 0
    while start < len(words):
        end, length = start, 0
        while end < len(words) and length + len(words[end]) + (end > start) <= chunk_size:
            length += len(words[end]) + (end > start)
            end += 1
        if end == start:  # a single word longer than a chunk
            windows.append(words[start][:chunk_size])
            start += 1
            continue
        windows.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        back, overlap_length = end, 0
        while back > start + 1 and overlap_length + len(words[back - 1]) + 1 <= overlap:
            back -= 1
            overlap_length += len(words[back]) + 1
        start = back
    return windows
