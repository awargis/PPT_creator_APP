"""Exam-aware question-start detection for JEE/NEET papers.

The key rule is: an option label such as ``(1)`` is never a question start.
Many PDFs split ``1.`` and the first line of the question into separate PDF
text blocks, so this module first joins those blocks before detecting the
question sequence.
"""

from __future__ import annotations

import re
from typing import Iterable

from models import BoundingBox, TextBlock

# Full question number + separator on the same PDF text block.
INLINE_Q_RE = re.compile(r"^\s*(?:question\s*|q\s*\.\s*)?(\d{1,3})\s*[\.)\-:]\s*(.*)$", re.I)
# Some PDFs store only ``17.`` as one block and the question text as another.
STANDALONE_Q_RE = re.compile(r"^\s*(\d{1,3})\s*[\.)\-:]?\s*$")
OPTION_RE = re.compile(r"^\s*\([1-4]\)\s*")
SECTION_RE = re.compile(r"\bsection\s*[-–—]?\s*(?:i{1,3}|iv|1|2|3)\b", re.I)
SUBJECT_RE = re.compile(r"\b(physics|chemistry|mathematics|maths|botany|zoology|biology)\b", re.I)


def question_match(text: str):
    text = text or ""
    m = INLINE_Q_RE.match(text)
    if m:
        return "plain", int(m.group(1))
    # Parenthesized numbers are options, not questions, in this paper family.
    if OPTION_RE.match(text):
        return None
    return None


def question_number(text: str):
    m = question_match(text)
    return m[1] if m else None


def _reading_key(block: TextBlock):
    # PDF pages in these papers are sequential columns: left column first,
    # then right column. This is crucial because q7 may sit above q2 visually.
    return (block.page_index, 99 if block.column_index == -1 else block.column_index, block.box.y0, block.box.x0)


def _union(a: BoundingBox, b: BoundingBox) -> BoundingBox:
    return BoundingBox(min(a.x0, b.x0), min(a.y0, b.y0), max(a.x1, b.x1), max(a.y1, b.y1))


def _join_split_number_blocks(blocks: list[TextBlock]) -> list[TextBlock]:
    """Join ``'1.'`` + ``'Find ...'`` when the PDF split them into blocks."""
    ordered = sorted(blocks, key=_reading_key)
    out: list[TextBlock] = []
    i = 0
    while i < len(ordered):
        b = ordered[i]
        m = STANDALONE_Q_RE.match((b.text or "").strip())
        if m and i + 1 < len(ordered):
            n = ordered[i + 1]
            same_stream = n.page_index == b.page_index and n.column_index == b.column_index
            close_y = abs(n.box.y0 - b.box.y0) <= 18
            # Never join an option/header/another numbered item.
            if same_stream and close_y and not OPTION_RE.match(n.text or "") and not STANDALONE_Q_RE.match((n.text or "").strip()):
                num = int(m.group(1))
                text = f"{num}. {n.text.strip()}"
                out.append(TextBlock(
                    text=text,
                    box=_union(b.box, n.box),
                    confidence=min(b.confidence, n.confidence),
                    page_index=b.page_index,
                    column_index=b.column_index,
                    block_type="question_start",
                    source=b.source,
                ))
                i += 2
                continue
        out.append(b)
        i += 1
    return out


def _candidate_score(block: TextBlock, number: int) -> float:
    text = (block.text or "").strip()
    score = block.confidence + 1.0
    if len(text) >= 12:
        score += 0.4
    if len(text) <= 4:
        score -= 0.4
    if OPTION_RE.match(text):
        score -= 5
    return score


def find_question_candidates(blocks: list[TextBlock]):
    prepared = _join_split_number_blocks(blocks)
    result = []
    for block in prepared:
        match = question_match(block.text)
        if match:
            kind, number = match
            result.append((block, kind, number, _candidate_score(block, number)))
    return result


def _deduplicate(candidates):
    unique = {}
    for block, kind, number, score in candidates:
        key = (block.page_index, block.column_index, number, round(block.box.y0 / 6))
        old = unique.get(key)
        if old is None or score > old[3]:
            unique[key] = (block, kind, number, score)
    return sorted(unique.values(), key=lambda x: _reading_key(x[0]))


def find_headers(blocks: list[TextBlock]) -> list[TextBlock]:
    """Return real subject/section headers, ignoring topic-summary lines."""
    explicit = []
    exact = []
    for block in blocks:
        text = " ".join((block.text or "").split()).strip()
        if not text or len(text) > 100 or question_number(text) is not None:
            continue
        low = text.lower()
        has_subject = bool(SUBJECT_RE.search(low))
        explicit_section = bool(re.match(r"^section\s*[-–—]?\s*(?:i{1,3}|iv|1|2|3)\b", low))
        exact_subject = bool(re.fullmatch(r"(?:section\s*[-–—]?\s*)?(physics|chemistry|mathematics|maths|botany|zoology|biology)", low))
        if has_subject and explicit_section:
            explicit.append(block)
        elif has_subject and exact_subject:
            exact.append(block)
    # If the document contains formal SECTION headers, they are authoritative
    # and topic-covered metadata on page 1 must not become a subject boundary.
    chosen = explicit if explicit else exact
    return sorted(chosen, key=_reading_key)

def _header_position(block):
    # Subject headers span the page conceptually even if PDF extraction assigns
    # them to one half-column. Compare by page + vertical position only.
    return (block.page_index, -1, block.box.y0, block.box.x0)

def _first_real_section_position(candidates, headers):
    if not headers:
        return None
    return _header_position(headers[0])


def _expected_numbers(exam_type: str):
    if exam_type == "JEE Main":
        return list(range(1, 76))
    if exam_type == "NEET UG":
        return list(range(1, 181))
    return None


def _header_subject(text: str):
    t = (text or "").lower()
    for name in ("physics", "chemistry", "mathematics", "maths", "botany", "zoology"):
        if name in t:
            return "Mathematics" if name == "maths" else name.title()
    return None

def _section_for_number(number, exam_type):
    if exam_type == "JEE Main":
        return "Physics" if number <= 25 else "Chemistry" if number <= 50 else "Mathematics"
    if exam_type == "NEET UG":
        return "Physics" if number <= 45 else "Chemistry" if number <= 90 else "Botany" if number <= 135 else "Zoology"
    return None

def _candidate_position(item):
    b = item[0]
    return (b.page_index, b.box.y0, b.box.x0)

def _select_by_sequence(candidates, expected_numbers, start_position=None, headers=None, exam_type=None):
    """Select one strong candidate per logical question number.

    Section headers are used as hard spatial guards, which prevents PDF
    fragments such as ``21. ×`` in a later chemistry page from stealing the
    real Physics Q21.
    """
    usable = [c for c in candidates if start_position is None or _candidate_position(c) >= start_position]
    header_events = []
    for h in headers or []:
        subject = _header_subject(h.text)
        if subject:
            header_events.append((_candidate_position((h, '', 0, 0)), subject))
    header_events.sort()

    def allowed(item, number):
        if not header_events or exam_type not in ("JEE Main", "NEET UG"):
            return True
        wanted = _section_for_number(number, exam_type)
        if not wanted:
            return True
        pos = _candidate_position(item)
        current = None
        for hpos, subj in header_events:
            if hpos <= pos:
                current = subj
            else:
                break
        return current == wanted

    by_number = {}
    for item in usable:
        if allowed(item, item[2]):
            by_number.setdefault(item[2], []).append(item)

    selected = []
    for number in expected_numbers:
        options = by_number.get(number, [])
        if not options:
            break
        options.sort(key=lambda x: (-x[3], x[0].page_index, x[0].box.y0, x[0].box.x0))
        selected.append(options[0][0])
    return selected

def find_questions(blocks: list[TextBlock], exam_type: str | None = None, headers: list[TextBlock] | None = None) -> list[TextBlock]:
    candidates = _deduplicate(find_question_candidates(blocks))
    headers = headers or []

    expected = _expected_numbers(exam_type or "")
    first_section = _first_real_section_position(candidates, headers)
    if expected:
        selected = _select_by_sequence(candidates, expected, first_section, headers=headers, exam_type=exam_type)
        # Require a substantial sequence. For the sample JEE Main this should
        # be all 75 questions; for damaged PDFs we still return a useful prefix.
        if len(selected) >= min(10, len(expected)):
            return selected

    # Generic fallback: start at the first real q1 after the first section and
    # follow consecutive numbers. This is safer than treating (1)-(4) as q's.
    usable = [c for c in candidates if first_section is None or (c[0].page_index, -1, c[0].box.y0, c[0].box.x0) >= first_section]
    selected = []
    expected_num = 1
    for item in usable:
        if item[2] == expected_num:
            selected.append(item[0])
            expected_num += 1
    return selected
