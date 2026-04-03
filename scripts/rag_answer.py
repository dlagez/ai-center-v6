import argparse
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.llm import chat_completion


def build_context(results: list[dict]) -> str:
    sections: list[str] = []
    for index, item in enumerate(results, start=1):
        source = item.get("source", "")
        headers = " > ".join(item.get("headers", []))
        title = f"[Chunk {index}] source={source}"
        if headers:
            title += f" headers={headers}"
        sections.append(f"{title}\n{item.get('text', '')}")
    return "\n\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve knowledge chunks and generate an answer.")
    parser.add_argument("question", help="User question.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of retrieved chunks.")
    parser.add_argument("--host", default="127.0.0.1", help="Knowledge API host.")
    parser.add_argument("--port", type=int, default=8000, help="Knowledge API port.")
    parser.add_argument("--model", default=None, help="Optional chat model override.")
    parser.add_argument("--max-tokens", type=int, default=1200, help="Maximum answer tokens.")
    args = parser.parse_args()

    response = requests.post(
        f"http://{args.host}:{args.port}/knowledge/search",
        json={"query": args.question, "limit": args.limit},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])

    if not results:
        print(
            json.dumps(
                {
                    "question": args.question,
                    "answer": "",
                    "sources": [],
                    "message": "No relevant chunks found.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    context = build_context(results)
    answer = chat_completion(
        model=args.model,
        max_tokens=args.max_tokens,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an enterprise knowledge assistant. "
                    "Answer only from the retrieved context. "
                    "Do not fabricate facts. "
                    "If the context is insufficient, say so clearly. "
                    "After the answer, include a short source list."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {args.question}\n\nRetrieved context:\n{context}",
            },
        ],
    )

    output = {
        "question": args.question,
        "answer": answer,
        "sources": [
            {
                "source": item.get("source", ""),
                "index": item.get("index", 0),
                "headers": item.get("headers", []),
                "score": item.get("score", 0.0),
            }
            for item in results
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
