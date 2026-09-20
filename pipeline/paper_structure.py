"""Automatic exam and paper-structure detection.

The structure detector intentionally uses evidence from the uploaded paper itself:
exam labels, section headers, question-range instructions, and question-type
headers.  Fixed JEE Main/NEET ranges are used only after the paper is identified.
"""

from dataclasses import dataclass, field
import re


@dataclass
class SectionSpec:
    subject: str
    start_number: int
    end_number: int
    page_index: int | None = None
    header_y: int | None = None
    question_types: dict[tuple[int, int], str] = field(default_factory=dict)

    def type_for(self, number: int) -> str:
        for (lo, hi), kind in self.question_types.items():
            if lo <= number <= hi:
                return kind
        return "MCQ"


@dataclass
class PaperStructure:
    exam_type: str
    sections: list[SectionSpec]
    instruction_pages: set[int] = field(default_factory=set)

    @property
    def ranges(self) -> list[tuple[int, int, str]]:
        return [(s.start_number, s.end_number, s.subject) for s in self.sections]

    def section_for(self, number: int) -> SectionSpec | None:
        for section in self.sections:
            if section.start_number <= number <= section.end_number:
                return section
        return None


SUBJECT_ALIASES = {
    "physics": "Physics",
    "chemistry": "Chemistry",
    "mathematics": "Mathematics",
    "maths": "Mathematics",
    "biology": "Biology",
    "botany": "Botany",
    "zoology": "Zoology",
}


def normalize_subject(text: str) -> str | None:
    lowered = text.lower()
    for alias, subject in SUBJECT_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            return subject
    return None


def detect_exam_type(page_text: str) -> tuple[str, float]:
    text = page_text.lower()
    if re.search(r"\bjee\s*advanced\b", text):
        return "JEE Advanced", 0.99
    if re.search(r"\bjee\s*main\b", text):
        return "JEE Main", 0.99
    if re.search(r"\bneet(?:\s*ug)?\b", text):
        return "NEET UG", 0.98
    if "joint entrance examination" in text:
        return "JEE Main", 0.70
    return "Unknown", 0.0


_RANGE_RE = re.compile(r"\((\d+)\s*[-–]\s*(\d+)\)")
_SECTION_RE = re.compile(r"section\s*[-–]?\s*[ivx]+\s*\(?\s*([a-z]+)\s*\)?", re.I)
_TYPE_RANGE_RE = re.compile(
    r"(single\s+correct|multiple\s+correct|integer|numerical|numerical\s+value|"
    r"matrix|match\s+the\s+following).*?\((\d+)\s*[-–]\s*(\d+)\)",
    re.I,
)


def _fixed_structure(exam_type: str) -> list[SectionSpec]:
    if exam_type == "JEE Main":
        return [
            SectionSpec("Physics", 1, 25, question_types={(1, 20): "MCQ", (21, 25): "Integer"}),
            SectionSpec("Chemistry", 26, 50, question_types={(26, 45): "MCQ", (46, 50): "Integer"}),
            SectionSpec("Mathematics", 51, 75, question_types={(51, 70): "MCQ", (71, 75): "Integer"}),
        ]
    if exam_type == "NEET UG":
        return [
            SectionSpec("Physics", 1, 45, question_types={(1, 45): "MCQ"}),
            SectionSpec("Chemistry", 46, 90, question_types={(46, 90): "MCQ"}),
            SectionSpec("Botany", 91, 135, question_types={(91, 135): "MCQ"}),
            SectionSpec("Zoology", 136, 180, question_types={(136, 180): "MCQ"}),
        ]
    return []


def build_structure(blocks_by_page: list[list], exam_type: str) -> PaperStructure:
    """Build an evidence-based structure from extracted page text."""
    fixed = _fixed_structure(exam_type)
    if fixed:
        # Attach actual section header locations where available.
        for page_index, blocks in enumerate(blocks_by_page):
            for block in blocks:
                subject = normalize_subject(block.text)
                if subject:
                    for section in fixed:
                        if section.subject == subject and re.search(
                            r"^\s*section\s*[-–]?\s*[ivx]+\s*\(",
                            block.text,
                            re.I,
                        ):
                            if section.page_index is None:
                                section.page_index = page_index
                                section.header_y = block.box.y0
        first_question_page = min(
            (s.page_index for s in fixed if s.page_index is not None),
            default=1,
        )
        return PaperStructure(
            exam_type=exam_type,
            sections=fixed,
            instruction_pages=set(range(first_question_page)),
        )

    # Generic JEE Advanced mode: derive sections and ranges from headers.
    sections: list[SectionSpec] = []
    pending: SectionSpec | None = None
    for page_index, blocks in enumerate(blocks_by_page):
        for block in blocks:
            text = block.text.strip()
            subject = normalize_subject(text)
            if "section" in text.lower() and subject:
                # If a section header itself doesn't provide a range, keep the
                # next question range as the section's bounds.
                pending = SectionSpec(subject, 1, 999, page_index, block.box.y0)
                sections.append(pending)
            m = _TYPE_RANGE_RE.search(text)
            if m and pending:
                lo, hi = int(m.group(2)), int(m.group(3))
                kind = "Integer" if "integer" in m.group(1).lower() or "numerical" in m.group(1).lower() else "MCQ"
                pending.question_types[(lo, hi)] = kind
                if pending.start_number == 1 and pending.end_number == 999:
                    pending.start_number, pending.end_number = lo, hi

    # If no section headers exist, retain a single review section. The actual
    # question detector will still expose detected questions.
    if not sections:
        sections = [SectionSpec("Unclassified", 1, 999)]

    # Remove overlapping placeholder ranges while preserving document order.
    return PaperStructure(
        exam_type=exam_type,
        sections=sections,
        instruction_pages={i for i, blocks in enumerate(blocks_by_page[:2]) if blocks},
    )
