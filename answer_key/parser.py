"""Robust answer-key parser for MCQ and integer/numerical keys.

Accepted examples::

    1: A
    Q2-B
    3) C
    4 -> D
    5: A/B
    21: 17
    22. -3
    23 = 12.5

The parser is intentionally line-oriented first so that question numbers from
one line cannot accidentally become answers for another question.
"""

import re

# A single answer token can be an option letter, option number, integer,
# decimal, negative value, fraction, or a slash-separated multi-answer.
_TOKEN = r"(?:-?\d+(?:\.\d+)?(?:/-?\d+(?:\.\d+)?)?|[A-Da-d])"
_MULTI_TOKEN = rf"{_TOKEN}(?:\s*[/&|]\s*{_TOKEN})*"

# Real-world answer keys frequently wrap every answer in parentheses, e.g.
# `1: (4), 2: (4), 21: (5), 75: (1.00)`.  The previous parser expected
# the token immediately after `:` and therefore returned an empty dictionary
# for this very common format. Keep the wrapper as part of the match and
# normalize it away later.
_VALUE = rf"(?:\(\s*{_MULTI_TOKEN}\s*\)|{_MULTI_TOKEN})"

_LINE_PATTERN = re.compile(
    rf"^\s*(?:Q\s*\.?\s*)?(\d{{1,3}})\s*(?::|\.|\)|=|->|-)\s*({_VALUE})",
    re.I,
)

# Some answer keys use `1 A` without punctuation.
_SPACE_PATTERN = re.compile(
    rf"^\s*(?:Q\s*\.?\s*)?(\d{{1,3}})\s+({_VALUE})",
    re.I,
)

_INLINE_PATTERN = re.compile(
    rf"(?:^|[,;])\s*(?:Q\s*\.?\s*)?(\d{{1,3}})\s*(?::|\.|\)|=|->|-)\s*({_VALUE})",
    re.I,
)


def _normalize(value: str) -> str:
    value = re.sub(r"\s+", "", value).upper()
    # Parentheses are presentation syntax in an answer key, not part of the
    # actual answer. Support both `(4)` and `4`, while retaining negatives,
    # decimals, fractions and slash-separated multi-answers.
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1]
    return value.replace("|", "/")


def parse(text: str) -> dict[int, str]:
    """Parse a pasted answer key into ``{question_number: answer}``.

    Line parsing is preferred. A final inline pass supports compact keys such
    as ``1:A, 2:B, 3:C``. Later duplicates intentionally overwrite earlier
    entries, matching the common workflow where a corrected key is pasted at
    the end.
    """
    result: dict[int, str] = {}
    source = text or ""

    for line in source.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _LINE_PATTERN.match(line) or _SPACE_PATTERN.match(line)
        if match:
            result[int(match.group(1))] = _normalize(match.group(2))

    for match in _INLINE_PATTERN.finditer(source):
        result[int(match.group(1))] = _normalize(match.group(2))

    return result
