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


def test_answer_key_parser_supports_parenthesized_full_jee_main_key():
    text = (
        "1: (4), 2: (4), 3: (2), 4: (3), 5: (2), 6: (1), 7: (3), 8: (4), "
        "9: (3), 10: (1), 11: (2), 12: (3), 13: (3), 14: (2), 15: (2), "
        "16: (2), 17: (4), 18: (1), 19: (2), 20: (4), 21: (5), 22: (4), "
        "23: (246), 24: (100), 25: (266), 26: (1), 27: (3), 28: (2), "
        "29: (2), 30: (4), 31: (4), 32: (4), 33: (3), 34: (1), 35: (2), "
        "36: (2), 37: (4), 38: (4), 39: (4), 40: (4), 41: (2), 42: (4), "
        "43: (3), 44: (3), 45: (2), 46: (0), 47: (332), 48: (486), "
        "49: (115), 50: (9), 51: (1), 52: (2), 53: (3), 54: (1), 55: (4), "
        "56: (4), 57: (3), 58: (4), 59: (1), 60: (3), 61: (1), 62: (3), "
        "63: (1), 64: (3), 65: (3), 66: (1), 67: (4), 68: (2), 69: (4), "
        "70: (4), 71: (5), 72: (1), 73: (757), 74: (5), 75: (1.00)"
    )
    answers = parse(text)
    assert len(answers) == 75
    assert answers[1] == "4"
    assert answers[20] == "4"
    assert answers[21] == "5"
    assert answers[23] == "246"
    assert answers[46] == "0"
    assert answers[47] == "332"
    assert answers[73] == "757"
    assert answers[75] == "1.00"
