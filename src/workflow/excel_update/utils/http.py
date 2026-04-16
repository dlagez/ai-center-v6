from urllib.parse import quote


def build_content_disposition(file_name: str) -> str:
    ascii_fallback = file_name.encode("ascii", "ignore").decode("ascii") or "download.xlsx"
    return (
        f'attachment; filename="{ascii_fallback}"; '
        f"filename*=UTF-8''{quote(file_name)}"
    )
