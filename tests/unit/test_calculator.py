
import pytest

from smart_notes.tools.calculator import calculate


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3", 5),
        ("2 + 3 * 4", 14),
        ("(2 + 3) * 4", 20),
        ("2 ** 10", 1024),
        ("-5 + 8", 3),
        ("10 % 3", 1),
    ],
)
def test_calculate_returns_correct_result(expression, expected):
    result = calculate(expression)

    assert result["success"] is True
    assert result["result"] == expected


@pytest.mark.parametrize(
    "expression",
    [
        "",
        "   ",
        "10 / 0",
        "__import__('os').system('whoami')",
        "unknown_variable + 1",
    ],
)
def test_calculate_rejects_invalid_expressions(expression):
    result = calculate(expression)

    assert result["success"] is False
    assert "error" in result


def test_calculate_rejects_expression_that_is_too_long():
    expression = "1" * 201

    result = calculate(expression)

    assert result["success"] is False
    assert result["error"] == "Expression is too long."
