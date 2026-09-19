"""Top-level coordinator for the local-first document pipeline."""

from .confidence import score_region
from .page_analyzer import analyze_page
from .pdf_loader import load_pdf
from .question_detector import find_headers, find_questions
from .question_segmenter import segment_questions
from .subject_classifier import classify_subjects
from .validator import validate_regions


def run_pipeline(pdf_bytes, exam_type, subjects, dpi=240, pad_x=24, pad_y=14, use_ocr=True, answers=None):
    loaded = load_pdf(pdf_bytes, dpi)
    all_blocks = []
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
            all_blocks.extend(analysis.blocks)
            all_headers.extend(find_headers(analysis.blocks))
    finally:
        loaded.document.close()

    # If formal SECTION headers exist anywhere in the document, discard
    # page-1 metadata such as "Topic Covered: Physics". Those lines are not
    # question-section boundaries.
    formal_headers = [
        h for h in all_headers
        if h.text.strip().lower().startswith("section-") or h.text.strip().lower().startswith("section ")
    ]
    effective_headers = formal_headers if formal_headers else all_headers

    all_questions = find_questions(all_blocks, exam_type=exam_type, headers=effective_headers)
    regions = segment_questions(loaded.pages, all_questions, pad_x, pad_y)
    regions = classify_subjects(regions, effective_headers, subjects, exam_type)
    for region in regions:
        region.confidence = score_region(region)
        if answers and region.number in answers:
            region.answer = answers[region.number]

    report = validate_regions(regions, answers)
    report.pages = len(loaded.pages)
    return regions, report
