"""Question-start and section-header detection."""

import re

from models import TextBlock

QUESTION_PATTERNS = (
    re.compile(r"^\s*(?:question\s*|q\s*\.\s*)?(\d{1,3})\s*[\.):\-]\s+", re.I),
    re.compile(r"^\s*\((\d{1,3})\)\s+"),
    re.compile(r"^\s*\[(\d{1,3})\]\s+"),
)
HEADER_WORDS = ("physics", "chemistry", "mathematics", "maths", "botany", "zoology", "biology")


def question_number(text: str):
    for pattern in QUESTION_PATTERNS:
        match = pattern.match(text or "")
        if match:
            return int(match.group(1))
    return None


def find_questions(blocks: list[TextBlock]) -> list[TextBlock]:
    starts = [block for block in blocks if question_number(block.text) is not None]
    # Duplicate detections can occur in OCR. Keep the strongest line at the
    # same page/column/number/vertical position.
    unique: dict[tuple[int, int, int, int], TextBlock] = {}
    for block in starts:
        number = question_number(block.text)
        key = (block.page_index, block.column_index, number, round(block.box.y0 / 3))
        current = unique.get(key)
        if current is None or block.confidence > current.confidence:
            unique[key] = block
    return sorted(unique.values(), key=lambda b: (b.page_index, b.column_index, b.box.y0))


def find_headers(blocks: list[TextBlock]) -> list[TextBlock]:
    headers = []
    for block in blocks:
        text = block.text.strip()
        lowered = text.lower()
        if len(text) <= 120 and any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in HEADER_WORDS):
            if question_number(text) is None:
                headers.append(block)
    return headers
