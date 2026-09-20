from answer_key.parser import parse


def test_answer_key_parser_supports_common_formats():
    answers = parse("1: A\nQ2-B\n3) C\n4 -> D\n5: A/B")
    assert answers == {1: "A", 2: "B", 3: "C", 4: "D", 5: "A/B"}


def test_answer_key_parser_supports_integer_and_compact_formats():
    answers = parse("21: 17\n22. -3\n23 = 12.5\n24: 1/2\n25 9\n26:A, 27:B, 28: 42")
    assert answers == {
        21: "17", 22: "-3", 23: "12.5", 24: "1/2", 25: "9",
        26: "A", 27: "B", 28: "42",
    }
