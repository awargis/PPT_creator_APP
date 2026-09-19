from answer_key.parser import parse


def test_answer_key_parser_supports_common_formats():
    answers = parse("1: A\nQ2-B\n3) C\n4 -> D\n5: A/B")
    assert answers == {1: "A", 2: "B", 3: "C", 4: "D", 5: "A/B"}
