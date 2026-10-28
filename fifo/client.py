import os
import sys
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REQUEST_FIFO = BASE_DIR / "request.fifo"
RESPONSE_FIFO = BASE_DIR / "response.fifo"


def main():
    if not REQUEST_FIFO.exists() or not RESPONSE_FIFO.exists():
        print("Server is not running. Start server.py first.")
        sys.exit(1)

    expression = " ".join(sys.argv[1:]).strip()

    if not expression:
        expression = input("Enter expression: ").strip()

    if not expression:
        print("Expression cannot be empty.")
        sys.exit(1)

    if "\n" in expression or "\r" in expression or "|" in expression:
        print("Invalid expression.")
        sys.exit(1)

    client_id = uuid.uuid4().hex

    with open(REQUEST_FIFO, "w", encoding="utf-8") as destination:
        destination.write(f"{client_id}|{expression}\n")

    with open(RESPONSE_FIFO, "r", encoding="utf-8") as source:
        response = source.readline().strip()

    print(f"Expression: {expression}")
    print(f"Server response: {response}")


if __name__ == "__main__":
    main()
