"""Flexible answer-key parser for MCQ and integer/numerical keys.

The answer-key input is deliberately permissive because teachers commonly paste
keys copied from PDFs, WhatsApp, Excel, answer sheets, or another application.
The parser maps *question number -> answer* and does not depend on the order in
which questions appear.

Examples accepted include::

    1: A, 2: B, 3: C
    1: (4), 2: (4), 3: (2)
    3: (2), 1: (4), 2: (4)          # arbitrary order
    Q1-A   Q2-B   Q3-C
    Question 1: A   Question 2: B
    1) A   2) B   3) C
    1. A   2. B   3. C
    1 -> A   2 -> B
    21: 17   22: -3   23: 12.5
    1 A\n2 B\n3 C
    [1] A   [2] B
    Ans 1: A, Ans 2: B

Parentheses around an answer are treated as presentation syntax, so ``(4)``
becomes ``4`` and ``(1.00)`` becomes ``1.00``.
"""

import re

# Answers may be option letters, option numbers, integers, decimals, fractions,
# negative values, or slash-separated combinations. We intentionally keep this
# conservative so ordinary text around the key is not swallowed.
_TOKEN = r"(?:-?\d+(?:\.\d+)?(?:/-?\d+(?:\.\d+)?)?|[A-Da-d])"
_MULTI_TOKEN = rf"{_TOKEN}(?:\s*[/&|]\s*{_TOKEN})*"
_VALUE = rf"(?:\(\s*{_MULTI_TOKEN}\s*\)|{_MULTI_TOKEN})"

# Explicit separators. The optional `answer/ans/question/q` label makes the
# parser tolerant of common copied answer-key headings and table exports.
_KEY_PREFIX = r"(?:answer|ans|question|ques|q)?\s*\.?\s*(\d{1,3})"
_EXPLICIT = re.compile(
    rf"(?<![A-Za-z0-9_(]){_KEY_PREFIX}\s*(?::|=|->|\)|\]|-|\.)\s*({_VALUE})(?![A-Za-z0-9_])",
    re.I,
)

# Bracketed question numbers: [1] A, [2] (B).
_BRACKETED = re.compile(
    rf"(?<![A-Za-z0-9_])\[\s*(\d{{1,3}})\s*\]\s*({_VALUE})(?![A-Za-z0-9_])",
    re.I,
)

# Whitespace-only format: `1 A`, `Q2 B`, `Question 3 (C)`.
# This is applied line-by-line to avoid treating arbitrary prose as a key.
_SPACE_LINE = re.compile(
    rf"^\s*(?:answer|ans|question|ques|q)?\s*\.?\s*(\d{{1,3}})\s+({_VALUE})(?:\s|$)",
    re.I,
)

# For compact whitespace-separated keys on one line, find a number followed by
# an answer and require that another key-like token follows or the text ends.
_SPACE_COMPACT = re.compile(
    rf"(?<![A-Za-z0-9_])(?:answer|ans|question|ques|q)?[ \t]*\.?[ \t]*(\d{{1,3}})[ \t]+({_VALUE})(?=[ \t]+(?:(?:answer|ans|question|ques|q)?[ \t]*\.?[ \t]*\d{{1,3}}[ \t]+)|[ \t]*$)",
    re.I,
)


def _normalize(value: str) -> str:
    value = re.sub(r"\s+", "", value).upper()
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1]
    return value.replace("|", "/")


def _put(result: dict[int, str], number: str, value: str) -> None:
    """Store one answer, ignoring malformed/out-of-range question numbers."""
    try:
        qno = int(number)
    except (TypeError, ValueError):
        return
    if qno < 1:
        return
    answer = _normalize(value)
    if answer:
        # Last occurrence wins intentionally: useful when a teacher pastes a
        # corrected key after an earlier version in the same text box.
        result[qno] = answer


def parse(text: str) -> dict[int, str]:
    """Parse an answer key into ``{question_number: answer}``.

    Parsing is independent of question order. All recognized entries are
    collected from the entire input, so keys may be shuffled, comma-separated,
    semicolon-separated, line-separated, or copied in common PDF/table forms.
    """
    result: dict[int, str] = {}
    source = text or ""
    if not source.strip():
        return result

    # 1) Explicit punctuation/bracket formats work regardless of ordering and
    # even when many entries share one line.
    for match in _EXPLICIT.finditer(source):
        _put(result, match.group(1), match.group(2))

    for match in _BRACKETED.finditer(source):
        _put(result, match.group(1), match.group(2))

    # 2) Whitespace-only formats are line-safe first.
    for line in source.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _SPACE_LINE.match(line)
        if match:
            _put(result, match.group(1), match.group(2))

    # 3) Finally support compact `1 A 2 B 3 C` style text.
    for match in _SPACE_COMPACT.finditer(source):
        _put(result, match.group(1), match.group(2))

    return result
