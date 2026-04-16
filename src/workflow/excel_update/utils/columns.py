import re

_EXCEL_COLUMN_RE = re.compile(r"^[A-Z]{1,4}$")


def normalize_excel_column(value: str) -> str:
    normalized = value.strip().upper()
    if not _EXCEL_COLUMN_RE.fullmatch(normalized):
        raise ValueError("invalid excel column name")
    return normalized
