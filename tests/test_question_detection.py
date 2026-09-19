from models import BoundingBox, TextBlock
from pipeline.question_detector import find_questions


def block(text, y, page=0, col=0):
    return TextBlock(text, BoundingBox(40, y, 550, y + 20), page_index=page, column_index=col)


def test_split_question_number_and_text_are_joined():
    blocks = [
        block("1.", 20), block("Which statement is correct?", 20),
        block("(1) First option", 60), block("(2) Second option", 90),
        block("2.", 140), block("Find the value of x.", 140),
        block("(1) 5", 180), block("(2) 6", 210),
        block("3.", 260), block("Next question", 260),
    ]
    questions = find_questions(blocks, "JEE Main")
    assert [q.text for q in questions] == [
        "1. Which statement is correct?", "2. Find the value of x.", "3. Next question"
    ]


def test_two_column_reading_order():
    blocks = [
        block("1.", 20, col=0), block("First", 20, col=0),
        block("2.", 100, col=0), block("Second", 100, col=0),
        block("3.", 20, col=1), block("Third", 20, col=1),
        block("4.", 100, col=1), block("Fourth", 100, col=1),
    ]
    questions = find_questions(blocks, "JEE Main")
    assert [q.text for q in questions] == ["1. First", "2. Second", "3. Third", "4. Fourth"]


def test_instruction_page_is_skipped_before_section_header():
    blocks = [
        block("1. Read instructions", 100, page=0),
        block("2. Four options", 140, page=0),
        block("SECTION-I (PHYSICS)", 500, page=0),
        block("1.", 40, page=1), block("Real question", 40, page=1),
        block("2.", 100, page=1), block("Second question", 100, page=1),
    ]
    headers = [blocks[2]]
    questions = find_questions(blocks, "JEE Main", headers=headers)
    assert [q.text for q in questions] == ["1. Real question", "2. Second question"]
