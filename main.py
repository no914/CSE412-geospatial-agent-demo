import os

from dotenv import load_dotenv
from google import genai

from agent import MODEL, ask

load_dotenv()


def main():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    print(f"Geospatial database agent ({MODEL}). Type 'quit' to exit.\n")

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue
        if question.lower() in {"quit", "exit"}:
            break

        try:
            result = ask(question, client=client, verbose=True)
        except Exception as exc:
            print(f"FAILED: {exc}\n")
            continue

        if result["error"]:
            print(f"FAILED: {result['error']}\n")
        else:
            print(result["answer"])
            print(f"[{result['requests']} model requests, {result['seconds']}s]\n")


if __name__ == "__main__":
    main()
