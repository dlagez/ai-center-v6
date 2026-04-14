from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.session import init_db


def main() -> None:
    init_db()
    print("Database tables initialized.")


if __name__ == "__main__":
    main()
