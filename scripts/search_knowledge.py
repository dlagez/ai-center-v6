import argparse
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Call the local knowledge search API.")
    parser.add_argument("query", help="Query text for vector search.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of chunks to return.")
    parser.add_argument("--host", default="127.0.0.1", help="API host.")
    parser.add_argument("--port", type=int, default=8000, help="API port.")
    args = parser.parse_args()

    response = requests.post(
        f"http://{args.host}:{args.port}/knowledge/search",
        json={"query": args.query, "limit": args.limit},
        timeout=120,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
#python scripts\rag_answer.py "这套方案的基本思路是什么？" --limit 5
