import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.service import KnowledgeIngestionService


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse documents with Docling and index them into Qdrant.")
    parser.add_argument("source", nargs="?", default="data/raw", help="File or directory to ingest.")
    args = parser.parse_args()

    service = KnowledgeIngestionService()
    summary = service.ingest_path(Path(args.source))
    print(
        f"Ingested {summary.documents} document(s), {summary.chunks} chunk(s) "
        f"into {summary.collection}"
    )


if __name__ == "__main__":
    main()
