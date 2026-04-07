import argparse
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Call the local SQL agent API.")
    parser.add_argument("question", help="Question for the SQL agent.")
    parser.add_argument("--db-path", default=None, help="SQLite database file path.")
    parser.add_argument("--max-rows", type=int, default=20, help="Maximum number of rows to read.")
    parser.add_argument("--host", default="127.0.0.1", help="API host.")
    parser.add_argument("--port", type=int, default=8000, help="API port.")
    args = parser.parse_args()

    payload = {
        "question": args.question,
        "max_rows": args.max_rows,
    }
    if args.db_path:
        payload["db_path"] = args.db_path

    response = requests.post(
        f"http://{args.host}:{args.port}/agents/sql",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
