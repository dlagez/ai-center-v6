from pathlib import Path

from src.knowledge.parser import DoclingParser


def main() -> None:
    parser = DoclingParser()

    file_path = Path("data/raw/example.pdf")
    parsed = parser.parse(file_path)

    print(parsed.text[:2000])


if __name__ == "__main__":
    main()
