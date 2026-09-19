"""Deterministic, explainable subject classification."""

from services.subject_service import normalize_subject


def classify_subjects(regions, headers, known_subjects, exam_type):
    ordered_headers = sorted(
        headers,
        key=lambda item: (item.page_index, item.column_index, item.box.y0),
    )
    for region in regions:
        subject = None
        # Prefer the most recent explicit section header in the same document
        # position. This is especially important for JEE Advanced.
        for header in ordered_headers:
            if (header.page_index, header.column_index, header.box.y0) <= (
                region.page_index,
                region.column_index,
                region.box.y0,
            ):
                subject = normalize_subject(header.text, known_subjects) or subject

        # Fixed numbering is used only where the exam specification itself is
        # fixed and unambiguous. JEE Advanced deliberately has no such fallback.
        if subject is None and exam_type == "JEE Main":
            if 1 <= region.number <= 25:
                subject = "Physics"
            elif 26 <= region.number <= 50:
                subject = "Chemistry"
            elif 51 <= region.number <= 75:
                subject = "Mathematics"
        elif subject is None and exam_type == "NEET UG":
            if 1 <= region.number <= 45:
                subject = "Physics"
            elif 46 <= region.number <= 90:
                subject = "Chemistry"
            elif 91 <= region.number <= 135:
                subject = "Botany"
            elif 136 <= region.number <= 180:
                subject = "Zoology"

        region.subject = subject if subject in known_subjects else "Unclassified"
        region.needs_review = region.subject == "Unclassified"
    return regions
