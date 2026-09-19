"""Turn detected question starts into complete question image regions."""

from PIL import Image

from models import BoundingBox, QuestionRegion, TextBlock
from .question_detector import question_number


def _column_bounds(page_width: int, column_index: int, two_columns: bool):
    if not two_columns or column_index == -1:
        return 0, page_width
    return (page_width // 2, page_width) if column_index == 1 else (0, page_width // 2)


def _reading_key(block):
    return (block.page_index, 99 if block.column_index == -1 else block.column_index, block.box.y0, block.box.x0)


def _next_in_same_stream(ordered, index):
    start = ordered[index]
    for candidate in ordered[index + 1:]:
        if candidate.column_index == start.column_index and candidate.page_index >= start.page_index:
            return candidate
    return None


def _crop_stream(page_images, start, next_start, pad_x, pad_y, page_columns):
    first = start.page_index
    last = next_start.page_index if next_start is not None else len(page_images) - 1
    pieces = []

    for page_index in range(first, last + 1):
        page = page_images[page_index]
        two_columns = len(page_columns.get(page_index, set())) > 1
        # Keep the question in the same column when the page is genuinely two-column.
        col = start.column_index if two_columns else -1
        left, right = _column_bounds(page.width, col, two_columns)
        x0 = max(0, left + pad_x)
        x1 = min(page.width, right - pad_x)

        y0 = max(0, start.box.y0 - pad_y) if page_index == first else pad_y
        if next_start is not None and page_index == next_start.page_index and next_start.column_index == start.column_index:
            y1 = min(page.height, next_start.box.y0 - max(2, pad_y // 2))
        else:
            y1 = page.height - pad_y

        if x1 > x0 and y1 > y0:
            pieces.append(page.crop((x0, y0, x1, y1)))

        if next_start is not None and page_index == next_start.page_index and next_start.column_index == start.column_index:
            break

    if not pieces:
        raise ValueError(f"Invalid crop for question {question_number(start.text)}")
    if len(pieces) == 1:
        return pieces[0]

    width = max(p.width for p in pieces)
    gap = 12
    canvas = Image.new("RGB", (width, sum(p.height for p in pieces) + gap * (len(pieces) - 1)), "white")
    y = 0
    for piece in pieces:
        canvas.paste(piece, (0, y))
        y += piece.height + gap
    return canvas


def segment_questions(page_images, questions: list[TextBlock], pad_x=24, pad_y=14):
    ordered = sorted(questions, key=_reading_key)
    page_columns = {}
    for q in ordered:
        page_columns.setdefault(q.page_index, set()).add(q.column_index)

    output = []
    for i, start in enumerate(ordered):
        number = question_number(start.text)
        if number is None:
            continue
        next_start = _next_in_same_stream(ordered, i)
        page = page_images[start.page_index]
        two_columns = len(page_columns.get(start.page_index, set())) > 1
        left, right = _column_bounds(page.width, start.column_index, two_columns)
        x0, x1 = max(0, left + pad_x), min(page.width, right - pad_x)
        y0 = max(0, start.box.y0 - pad_y)
        if next_start is not None and next_start.page_index == start.page_index and next_start.column_index == start.column_index:
            y1 = min(page.height, next_start.box.y0 - max(2, pad_y // 2))
        else:
            y1 = page.height - pad_y
        if x1 <= x0 or y1 <= y0:
            continue
        try:
            image = _crop_stream(page_images, start, next_start, pad_x, pad_y, page_columns)
        except ValueError:
            continue
        output.append(QuestionRegion(
            number=number,
            page_index=start.page_index,
            column_index=start.column_index,
            box=BoundingBox(x0, y0, x1, y1).clamp(page.width, page.height),
            image=image,
            ocr_text=start.text,
            confidence=max(0.0, min(1.0, start.confidence)),
            extraction_method=start.source,
            end_page_index=(next_start.page_index if next_start else start.page_index),
        ))
    return output
