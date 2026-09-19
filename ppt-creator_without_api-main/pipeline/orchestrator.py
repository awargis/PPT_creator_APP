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
    all_questions = []
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
            all_questions.extend(find_questions(analysis.blocks))
            all_headers.extend(find_headers(analysis.blocks))
    finally:
        loaded.document.close()

    regions = segment_questions(loaded.pages, all_questions, pad_x, pad_y)
    regions = classify_subjects(regions, all_headers, subjects, exam_type)
    for region in regions:
        region.confidence = score_region(region)
        if answers and region.number in answers:
            region.answer = answers[region.number]

    report = validate_regions(regions, answers)
    report.pages = len(loaded.pages)
    return regions, report
