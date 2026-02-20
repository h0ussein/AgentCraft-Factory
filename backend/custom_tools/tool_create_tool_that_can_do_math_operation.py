def do_math_operation(expression: str) -> str:
    """
    Performs a mathematical operation given an expression string.
    The expression can include basic arithmetic operations (+, -, *, /, **, %),
    and numbers.
    Example: "2 + 2", "10 / 3", "(5 * 2) - 1".
    """
    try:
        # Evaluate the mathematical expression.
        # Using eval() can be risky with untrusted input.
        # For this tool, we assume the input is a safe mathematical expression.
        result = eval(expression)
        return str(result)
    except SyntaxError:
        return "Invalid mathematical expression. Please check the syntax."
    except NameError:
        return "Invalid mathematical expression. Only numbers and basic operators are allowed."
    except TypeError:
        return "Invalid mathematical expression. Please ensure correct types for operations."
    except ZeroDivisionError:
        return "Error: Division by zero is not allowed."
    except Exception as e:
        return f"An unexpected error occurred: {e}"