import ast
import operator
import os
import signal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REQUEST_FIFO = BASE_DIR / "request.fifo"
RESPONSE_FIFO = BASE_DIR / "response.fifo"

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calculate(expression):
    if len(expression) > 200:
        raise ValueError("Expression is too long")

    tree = ast.parse(expression, mode="eval")

    def evaluate(node, depth=0):
        if depth > 20:
            raise ValueError("Expression is too complex")

        if isinstance(node, ast.Expression):
            return evaluate(node.body, depth + 1)

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            left = evaluate(node.left, depth + 1)
            right = evaluate(node.right, depth + 1)

            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("Exponent is too large")

            result = OPERATORS[type(node.op)](left, right)

            if isinstance(result, (int, float)):
                if abs(result) > 10**100:
                    raise ValueError("Result is too large")

            return result

        if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](
                evaluate(node.operand, depth + 1)
            )

        raise ValueError("Unsupported expression")

    result = evaluate(tree)

    if isinstance(result, float) and not __import__("math").isfinite(result):
        raise ValueError("Result is not finite")

    return result


def main():
    for fifo in (REQUEST_FIFO, RESPONSE_FIFO):
        if fifo.exists():
            if not fifo.is_fifo():
                raise RuntimeError(f"{fifo} exists but is not a FIFO")
            fifo.unlink()
        os.mkfifo(fifo, 0o600)

    print("FIFO server started.")
    print(f"Request FIFO: {REQUEST_FIFO}")
    print(f"Response FIFO: {RESPONSE_FIFO}")
    print("Waiting for clients. Press Ctrl+C to stop.")

    try:
        while True:
            with open(REQUEST_FIFO, "r", encoding="utf-8") as source:
                request = source.readline().strip()

            if not request:
                continue

            client_id, expression = request.split("|", 1)

            if client_id == "STOP":
                break

            try:
                result = calculate(expression)
                response = f"OK|{result}\n"
            except Exception as error:
                response = f"ERROR|{error}\n"

            with open(RESPONSE_FIFO, "w", encoding="utf-8") as destination:
                destination.write(response)

            print(f"Request: {expression} -> {response.strip()}")

    except KeyboardInterrupt:
        print("\nStopping server.")

    finally:
        for fifo in (REQUEST_FIFO, RESPONSE_FIFO):
            if fifo.exists() and fifo.is_fifo():
                fifo.unlink()

        print("FIFO files removed.")


if __name__ == "__main__":
    main()
