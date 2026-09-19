"""Tolerant answer-key parser for pasted/plain-text keys."""

import re

_TOKEN = r"(?:[A-Da-d]|[1-4])"
_PATTERN = re.compile(
    rf"(?:^|[\n,;])\s*(?:Q\.?\s*)?(\d{{1,3}})\s*(?:[:.\-)=]|->|\s)\s*\(?\s*({_TOKEN}(?:\s*[,/&|]\s*{_TOKEN})*)",
    re.I,
)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).upper().replace("|", "/")


def parse(text: str) -> dict[int, str]:
    result: dict[int, str] = {}
    for match in _PATTERN.finditer(text or ""):
        result[int(match.group(1))] = _normalize(match.group(2))
    return result
