import socket
import sys
from pathlib import Path

SOCKET_PATH = Path(__file__).resolve().parent / "calculator.sock"


def main():
    expression = " ".join(sys.argv[1:]).strip()

    if not expression:
        expression = input("Enter expression: ").strip()

    if not expression:
        print("Expression cannot be empty.")
        return

    if "\n" in expression or "\r" in expression:
        print("Invalid expression.")
        return

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(SOCKET_PATH))
            client.sendall(expression.encode("utf-8"))
            client.shutdown(socket.SHUT_WR)

            response = client.recv(4096).decode("utf-8").strip()

        print(f"Expression: {expression}")
        print(f"Server response: {response}")

    except FileNotFoundError:
        print("Server is not running. Start server.py first.")

    except ConnectionRefusedError:
        print("Connection refused. Restart the server.")


if __name__ == "__main__":
    main()
