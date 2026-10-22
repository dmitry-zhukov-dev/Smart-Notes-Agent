
"""A safe calculator tool for basic mathematical expressions."""

import ast
import math
import operator


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_MAX_EXPRESSION_LENGTH = 200
_MAX_ABS_VALUE = 1e100
_MAX_EXPONENT = 1000


def _evaluate_node(node: ast.AST) -> int | float:
    """Evaluate only explicitly supported mathematical AST nodes."""
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(
            node.value, (int, float)
        ):
            raise ValueError("Only numeric constants are allowed.")

        return node.value

    if isinstance(node, ast.BinOp):
        operation = _BINARY_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("This mathematical operator is not supported.")

        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)

        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError("Exponent is too large.")

        result = operation(left, right)
        return _validate_result(result)

    if isinstance(node, ast.UnaryOp):
        operation = _UNARY_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("This unary operator is not supported.")

        result = operation(_evaluate_node(node.operand))
        return _validate_result(result)

    raise ValueError("Invalid or unsupported mathematical expression.")


def _validate_result(value: int | float) -> int | float:
    """Reject non-finite and excessively large results."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Calculation did not produce a number.")

    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Result must be a finite number.")

    if abs(value) > _MAX_ABS_VALUE:
        raise ValueError("Result is too large.")

    return value


def calculate(expression: str) -> dict[str, object]:
    """Calculate a basic mathematical expression safely."""
    if not isinstance(expression, str) or not expression.strip():
        return {
            "success": False,
            "error": "Expression must not be empty.",
        }

    expression = expression.strip()

    if len(expression) > _MAX_EXPRESSION_LENGTH:
        return {
            "success": False,
            "error": "Expression is too long.",
        }

    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate_node(tree)

        return {
            "success": True,
            "expression": expression,
            "result": result,
        }

    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError):
        return {
            "success": False,
            "error": "Invalid expression or calculation error.",
        }
