from src.knowledge.parser import DoclingParser


class _FakeDocument:
    def export_to_markdown(self) -> str:
        return "# Parsed"


class _FakeResult:
    def __init__(self) -> None:
        self.document = _FakeDocument()


def test_docling_parser_uses_converter(monkeypatch) -> None:
    parser = DoclingParser()

    def fake_convert(source):
        assert str(source) == "demo.pdf"
        return _FakeResult()

    monkeypatch.setattr(parser.converter, "convert", fake_convert)

    parsed = parser.parse("demo.pdf")

    assert parsed.source == "demo.pdf"
    assert parsed.text == "# Parsed"
