"""Deterministic exam-type detection from the first pages of a paper.

This is deliberately local and explainable: no external API is required.
The detector returns evidence and confidence so the UI can show what caused
the classification and still allow a manual override.
"""

from dataclasses import dataclass
import re
import fitz


@dataclass(frozen=True)
class ExamDetection:
    exam_type: str
    confidence: float
    evidence: tuple[str, ...]


def _score(text: str):
    t = re.sub(r"\s+", " ", text.lower())
    scores = {"JEE Main": 0.0, "JEE Advanced": 0.0, "NEET UG": 0.0}
    evidence = {"JEE Main": [], "JEE Advanced": [], "NEET UG": []}

    def add(exam, points, phrase):
        scores[exam] += points
        evidence[exam].append(phrase)

    if re.search(r"jee\s*\(?\s*advanced", t):
        add("JEE Advanced", 8, "JEE Advanced")
    if "jee (advanced)" in t or "joint entrance examination (advanced)" in t:
        add("JEE Advanced", 4, "Advanced exam wording")
    if re.search(r"jee\s*main", t):
        add("JEE Main", 7, "JEE Main")
    if re.search(r"\bnta\b", t):
        add("JEE Main", 2, "NTA")
    if "neet" in t:
        add("NEET UG", 8, "NEET")
    if "national eligibility cum entrance test" in t:
        add("NEET UG", 4, "NEET full name")

    # Strong structural fingerprints.
    if re.search(r"\bphysics\b.{0,120}\bchemistry\b.{0,120}\bmathematics\b", t):
        add("JEE Main", 3, "Physics/Chemistry/Mathematics sequence")
    if all(word in t for word in ("physics", "chemistry", "botany", "zoology")):
        add("NEET UG", 5, "Physics/Chemistry/Botany/Zoology")
    if "integer type" in t or "numerical answer" in t or "multiple correct" in t:
        add("JEE Advanced", 3, "Advanced-style question types")
    if re.search(r"\b180\b.{0,80}\bquestions?\b", t):
        add("NEET UG", 4, "180-question structure")
    if re.search(r"\b75\b.{0,80}\bquestions?\b", t):
        add("JEE Main", 3, "75-question structure")

    return scores, evidence


def detect_exam_type(pdf_bytes: bytes, max_pages: int = 3) -> ExamDetection:
    if not pdf_bytes:
        return ExamDetection("JEE Main", 0.0, ("Empty PDF",))

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        chunks = []
        for page in list(doc)[:max_pages]:
            chunks.append(page.get_text("text") or "")
        text = "\n".join(chunks)
    finally:
        doc.close()

    scores, evidence = _score(text)
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    winner, top = ordered[0]
    second = ordered[1][1]
    if top <= 0:
        return ExamDetection("JEE Main", 0.0, ("No strong exam marker found",))

    # Confidence reflects both evidence strength and separation from runner-up.
    confidence = min(0.99, max(0.50, 0.50 + 0.05 * (top - second) + 0.025 * top))
    return ExamDetection(winner, confidence, tuple(dict.fromkeys(evidence[winner])))


def detect_exam_from_text(text: str) -> ExamDetection:
    scores, evidence = _score(text or "")
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    winner, top = ordered[0]
    second = ordered[1][1]
    if top <= 0:
        return ExamDetection("JEE Main", 0.0, ("No strong exam marker found",))
    confidence = min(0.99, max(0.50, 0.50 + 0.05 * (top - second) + 0.025 * top))
    return ExamDetection(winner, confidence, tuple(dict.fromkeys(evidence[winner])))
