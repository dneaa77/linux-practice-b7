import ast
import math
import operator
import os
import socket
from multiprocessing import Process
from pathlib import Path

SOCKET_PATH = Path(__file__).resolve().parent / "calculator.sock"

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

            if isinstance(result, (int, float)) and abs(result) > 10**100:
                raise ValueError("Result is too large")

            return result

        if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](
                evaluate(node.operand, depth + 1)
            )

        raise ValueError("Unsupported expression")

    result = evaluate(tree)

    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("Result is not finite")

    return result


def handle_client(connection):
    with connection:
        try:
            data = connection.recv(4096).decode("utf-8").strip()

            if not data:
                return

            result = calculate(data)
            response = f"OK|{result}"

        except Exception as error:
            response = f"ERROR|{error}"

        connection.sendall((response + "\n").encode("utf-8"))


def main():
    if SOCKET_PATH.exists():
        if not SOCKET_PATH.is_socket():
            raise RuntimeError(
                f"{SOCKET_PATH} exists but is not a socket"
            )
        SOCKET_PATH.unlink()

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        server.bind(str(SOCKET_PATH))
        os.chmod(SOCKET_PATH, 0o600)
        server.listen(10)

        print("Unix socket server started.")
        print(f"Socket: {SOCKET_PATH}")
        print("Waiting for clients. Press Ctrl+C to stop.")

        while True:
            connection, _ = server.accept()

            process = Process(
                target=handle_client,
                args=(connection,),
            )
            process.start()

            # The child process handles the accepted connection.
            connection.close()

    except KeyboardInterrupt:
        print("\nStopping server.")

    finally:
        server.close()

        if SOCKET_PATH.exists() and SOCKET_PATH.is_socket():
            SOCKET_PATH.unlink()

        print("Unix socket removed.")


if __name__ == "__main__":
    main()
