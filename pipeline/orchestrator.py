"""Top-level coordinator for the production local-first pipeline."""

from .confidence import score_region
from .page_analyzer import analyze_page
from .pdf_loader import load_pdf
from .question_detector import find_headers, find_questions
from .question_segmenter import segment_questions
from .paper_structure import build_structure, detect_exam_type
from .subject_classifier import classify_subjects
from .validator import validate_regions


def _blocks_to_text(blocks):
    return "\n".join(block.text for block in blocks if block.text)


def _section_window(blocks_by_page, section):
    """Return blocks belonging to one section, excluding instruction pages and
    the next subject section."""
    selected = []
    for page_index, blocks in enumerate(blocks_by_page):
        if section.page_index is not None and page_index < section.page_index:
            continue
        for block in blocks:
            if (
                section.page_index == page_index
                and section.header_y is not None
                and block.box.y1 < section.header_y
            ):
                continue
            # Stop at a later section header on the same page.
            if (
                page_index == section.page_index
                and section.header_y is not None
                and block.box.y0 < section.header_y
            ):
                continue
            selected.append(block)
    return selected


def run_pipeline(
    pdf_bytes,
    exam_type=None,
    subjects=None,
    dpi=240,
    pad_x=18,
    pad_y=10,
    use_ocr=True,
    answers=None,
):
    loaded = load_pdf(pdf_bytes, dpi)
    blocks_by_page = []
    all_headers = []
    try:
        for index, page in enumerate(loaded.document):
            analysis = analyze_page(
                page,
                loaded.pages[index],
                index,
                dpi=dpi,
                use_ocr=use_ocr,
                page_info=loaded.page_info[index],
            )
            blocks_by_page.append(analysis.blocks)
            all_headers.extend(find_headers(analysis.blocks))

        first_pages_text = "\n".join(
            _blocks_to_text(blocks) for blocks in blocks_by_page[:3]
        )
        detected_exam, exam_confidence = detect_exam_type(first_pages_text)
        if not exam_type or exam_type == "Auto":
            exam_type = detected_exam
        elif detected_exam != "Unknown" and exam_type != detected_exam:
            # The paper's explicit label wins over a stale UI selection.
            exam_type = detected_exam

        structure = build_structure(blocks_by_page, exam_type)
        expected = {
            n
            for section in structure.sections
            for n in range(section.start_number, section.end_number + 1)
            if section.end_number < 1000
        }

        all_questions = []
        if structure.sections and exam_type in {"JEE Main", "NEET UG"}:
            # Detect each section independently. This is what prevents page-1
            # instruction numbering from ever entering the question stream.
            for section in structure.sections:
                window = _section_window(blocks_by_page, section)
                found = find_questions(
                    window,
                    expected_numbers=set(range(section.start_number, section.end_number + 1)),
                    min_number=section.start_number,
                    max_number=section.end_number,
                )
                all_questions.extend(found)
        else:
            # JEE Advanced / unusual papers: use standalone/in-line question
            # markers after the detected section headers. Uncertain detections
            # remain reviewable rather than being silently discarded.
            start_page = min(structure.instruction_pages or {0})
            window = [
                block
                for page_index, blocks in enumerate(blocks_by_page)
                if page_index >= start_page
                for block in blocks
            ]
            all_questions = find_questions(window, expected_numbers=None)

        # De-duplicate by question number and choose the earliest structurally
        # valid marker. This also prevents OCR duplicates.
        unique = {}
        for q in all_questions:
            number = None
            from .question_detector import question_number
            number = question_number(q.text)
            if number is not None and number not in unique:
                unique[number] = q
        all_questions = sorted(
            unique.values(), key=lambda b: (b.page_index, b.column_index, b.box.y0)
        )

        regions = segment_questions(
            loaded.pages,
            all_questions,
            structure=structure,
            pad_x=pad_x,
            pad_y=pad_y,
        )
        effective_subjects = subjects or [
            section.subject for section in structure.sections
            if section.subject != "Unclassified"
        ]
        regions = classify_subjects(
            regions,
            all_headers,
            effective_subjects,
            exam_type,
            structure=structure,
        )

        for region in regions:
            region.confidence = score_region(region)
            if answers and region.number in answers:
                region.answer = answers[region.number]

        report = validate_regions(regions, answers)
        report.pages = len(loaded.pages)
        report.exam_type = exam_type
        report.exam_confidence = exam_confidence
        report.expected_questions = sum(
            s.end_number - s.start_number + 1
            for s in structure.sections
            if s.end_number < 1000
        )
        report.detected_questions = len(regions)
        return regions, report, structure
    finally:
        loaded.document.close()
