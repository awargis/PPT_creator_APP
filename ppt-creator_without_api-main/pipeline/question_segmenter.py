"""Convert question starts into safe page-image regions."""

from models import BoundingBox, QuestionRegion, TextBlock
from .question_detector import question_number


def _column_bounds(page_width: int, column_index: int, two_columns: bool) -> tuple[int, int]:
    if not two_columns or column_index == -1:
        return 0, page_width
    if column_index == 1:
        return page_width // 2, page_width
    return 0, page_width // 2


def segment_questions(page_images, questions: list[TextBlock], pad_x=24, pad_y=14):
    """Segment question regions from question-start lines.

    The region ends immediately before the next detected question in the same
    column. If no next question exists, it extends to the usable bottom of the
    page. Full-width question starts use the complete page width.
    """
    ordered = sorted(questions, key=lambda b: (b.page_index, b.column_index, b.box.y0))
    output = []
    two_column_pages = {
        page_index: any(b.page_index == page_index and b.column_index == 1 for b in ordered)
        for page_index in {b.page_index for b in ordered}
    }

    for index, start in enumerate(ordered):
        number = question_number(start.text)
        if number is None:
            continue
        page = page_images[start.page_index]
        next_start = None
        for candidate in ordered[index + 1 :]:
            if candidate.page_index != start.page_index:
                break
            if candidate.column_index == start.column_index:
                next_start = candidate
                break

        left, right = _column_bounds(page.width, start.column_index, two_column_pages.get(start.page_index, False))

        x0 = max(0, left + pad_x)
        x1 = min(page.width, right - pad_x)
        # Keep the question number and its text; don't cut the top line.
        y0 = max(0, start.box.y0 - max(2, pad_y))
        if next_start is not None:
            y1 = min(page.height, next_start.box.y0 - max(2, pad_y // 2))
        else:
            y1 = page.height - max(2, pad_y)

        if x1 <= x0 or y1 <= y0:
            continue
        box = BoundingBox(x0, y0, x1, y1).clamp(page.width, page.height)
        image = page.crop((box.x0, box.y0, box.x1, box.y1))
        output.append(
            QuestionRegion(
                number=number,
                page_index=start.page_index,
                column_index=start.column_index,
                box=box,
                image=image,
                ocr_text=start.text,
                confidence=max(0.0, min(1.0, start.confidence)),
                extraction_method=start.source,
            )
        )
    return output
