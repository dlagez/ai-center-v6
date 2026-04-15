import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile


XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass
class ZipEntrySummary:
    name: str
    file_size: int
    compress_size: int
    crc: int
    sha256: str
    category: str
    is_xml: bool


@dataclass
class WorksheetSummary:
    path: str
    title: str | None
    dimension: str | None
    row_count: int
    cell_count: int
    formula_count: int
    merged_range_count: int
    hyperlink_count: int
    table_count: int
    drawing_refs: list[str]
    comment_ref_count: int
    legacy_drawing_count: int


def classify_part(name: str) -> str:
    if name == "xl/vbaProject.bin":
        return "macro"
    if name.startswith("xl/media/"):
        return "media"
    if name.startswith("xl/drawings/"):
        return "drawing"
    if name.startswith("xl/comments"):
        return "comment"
    if name.startswith("xl/pivotCache/"):
        return "pivot_cache"
    if name.startswith("xl/pivotTables/"):
        return "pivot_table"
    if name.startswith("xl/externalLinks/"):
        return "external_link"
    if name.startswith("xl/embeddings/"):
        return "embedding"
    if name.startswith("xl/printerSettings/"):
        return "printer_settings"
    if name.startswith("xl/ctrlProps/"):
        return "control_property"
    if name.startswith("xl/worksheets/"):
        return "worksheet"
    if name.startswith("xl/charts/"):
        return "chart"
    if name.startswith("xl/theme/"):
        return "theme"
    if name.startswith("xl/styles"):
        return "style"
    if name.startswith("customXml/"):
        return "custom_xml"
    if name.startswith("docProps/"):
        return "document_property"
    if name.startswith("_rels/") or name.endswith(".rels"):
        return "relationship"
    if name == "[Content_Types].xml":
        return "content_types"
    if name.endswith(".xml"):
        return "xml_other"
    return "other"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_xml(payload: bytes) -> ET.Element | None:
    try:
        return ET.fromstring(payload)
    except ET.ParseError:
        return None


def safe_find_text(root: ET.Element | None, xpath: str, namespaces: dict[str, str]) -> str | None:
    if root is None:
        return None
    element = root.find(xpath, namespaces)
    if element is None:
        return None
    text = element.text
    return text.strip() if text else None


def list_zip_entries(workbook_path: Path) -> dict[str, ZipEntrySummary]:
    entries: dict[str, ZipEntrySummary] = {}
    with ZipFile(workbook_path) as archive:
        for info in archive.infolist():
            payload = archive.read(info.filename)
            entries[info.filename] = ZipEntrySummary(
                name=info.filename,
                file_size=info.file_size,
                compress_size=info.compress_size,
                crc=info.CRC,
                sha256=sha256_bytes(payload),
                category=classify_part(info.filename),
                is_xml=info.filename.endswith(".xml") or info.filename.endswith(".rels"),
            )
    return entries


def load_zip_payloads(workbook_path: Path) -> dict[str, bytes]:
    with ZipFile(workbook_path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def load_relationship_targets(payloads: dict[str, bytes], rel_path: str) -> dict[str, str]:
    root = parse_xml(payloads.get(rel_path, b""))
    if root is None:
        return {}

    targets: dict[str, str] = {}
    for rel in root.findall("pkgrel:Relationship", XML_NS):
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target:
            targets[rel_id] = target
    return targets


def normalize_relationship_target(base_path: str, target: str) -> str:
    base = PurePosixPath(base_path).parent
    pieces: list[str] = []
    for part in (base / target).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if pieces:
                pieces.pop()
            continue
        pieces.append(part)
    return PurePosixPath(*pieces).as_posix()


def load_sheet_title_map(payloads: dict[str, bytes]) -> dict[str, str]:
    workbook_root = parse_xml(payloads.get("xl/workbook.xml", b""))
    rel_map = load_relationship_targets(payloads, "xl/_rels/workbook.xml.rels")
    if workbook_root is None:
        return {}

    title_map: dict[str, str] = {}
    for sheet in workbook_root.findall("main:sheets/main:sheet", XML_NS):
        title = sheet.attrib.get("name")
        rel_id = sheet.attrib.get(f"{{{XML_NS['rel']}}}id")
        if not title or not rel_id:
            continue
        target = rel_map.get(rel_id)
        if not target:
            continue
        normalized = normalize_relationship_target("xl/workbook.xml", target)
        title_map[normalized] = title
    return title_map


def summarize_worksheet(payloads: dict[str, bytes], path: str, title: str | None) -> WorksheetSummary | None:
    root = parse_xml(payloads.get(path, b""))
    if root is None:
        return None

    rel_path = f"{Path(path).parent.as_posix()}/_rels/{Path(path).name}.rels"
    rel_map = load_relationship_targets(payloads, rel_path)

    drawing_refs: list[str] = []
    for node in root.findall("main:drawing", XML_NS):
        rel_id = node.attrib.get(f"{{{XML_NS['rel']}}}id")
        if rel_id and rel_id in rel_map:
            drawing_refs.append(normalize_relationship_target(path, rel_map[rel_id]))

    cell_count = 0
    formula_count = 0
    row_count = 0
    for row in root.findall(".//main:sheetData/main:row", XML_NS):
        row_count += 1
        for cell in row.findall("main:c", XML_NS):
            cell_count += 1
            if cell.find("main:f", XML_NS) is not None:
                formula_count += 1

    return WorksheetSummary(
        path=path,
        title=title,
        dimension=(root.find("main:dimension", XML_NS) or ET.Element("dimension")).attrib.get("ref"),
        row_count=row_count,
        cell_count=cell_count,
        formula_count=formula_count,
        merged_range_count=len(root.findall(".//main:mergeCells/main:mergeCell", XML_NS)),
        hyperlink_count=len(root.findall(".//main:hyperlinks/main:hyperlink", XML_NS)),
        table_count=len(root.findall(".//main:tableParts/main:tablePart", XML_NS)),
        drawing_refs=sorted(set(drawing_refs)),
        comment_ref_count=len(root.findall(".//main:legacyDrawingHF", XML_NS)),
        legacy_drawing_count=len(root.findall(".//main:legacyDrawing", XML_NS)),
    )


def summarize_workbook(workbook_path: Path) -> dict[str, Any]:
    payloads = load_zip_payloads(workbook_path)
    entries = list_zip_entries(workbook_path)
    categories = Counter(item.category for item in entries.values())
    sheet_title_map = load_sheet_title_map(payloads)

    worksheets: dict[str, WorksheetSummary] = {}
    for path, title in sheet_title_map.items():
        if path in payloads:
            summary = summarize_worksheet(payloads, path, title)
            if summary is not None:
                worksheets[path] = summary

    unknown_sheet_paths = sorted(
        name for name in payloads if name.startswith("xl/worksheets/") and name.endswith(".xml") and name not in worksheets
    )
    for path in unknown_sheet_paths:
        summary = summarize_worksheet(payloads, path, None)
        if summary is not None:
            worksheets[path] = summary

    return {
        "path": str(workbook_path),
        "file_size": workbook_path.stat().st_size,
        "entries": entries,
        "category_counts": dict(categories),
        "worksheets": worksheets,
    }


def diff_dict_values(left: dict[str, Any], right: dict[str, Any], fields: list[str]) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for field in fields:
        if left.get(field) != right.get(field):
            changes[field] = {"before": left.get(field), "after": right.get(field)}
    return changes


def build_report(original_path: Path, roundtrip_path: Path) -> dict[str, Any]:
    original = summarize_workbook(original_path)
    roundtrip = summarize_workbook(roundtrip_path)

    original_entries: dict[str, ZipEntrySummary] = original["entries"]
    roundtrip_entries: dict[str, ZipEntrySummary] = roundtrip["entries"]

    original_names = set(original_entries)
    roundtrip_names = set(roundtrip_entries)

    removed_entries = sorted(original_names - roundtrip_names)
    added_entries = sorted(roundtrip_names - original_names)
    changed_entries = sorted(
        name
        for name in (original_names & roundtrip_names)
        if original_entries[name].sha256 != roundtrip_entries[name].sha256
    )

    removed_by_category = Counter(original_entries[name].category for name in removed_entries)
    added_by_category = Counter(roundtrip_entries[name].category for name in added_entries)
    changed_by_category = Counter(original_entries[name].category for name in changed_entries)

    worksheet_diffs: list[dict[str, Any]] = []
    original_sheets: dict[str, WorksheetSummary] = original["worksheets"]
    roundtrip_sheets: dict[str, WorksheetSummary] = roundtrip["worksheets"]
    for path in sorted(set(original_sheets) | set(roundtrip_sheets)):
        before = original_sheets.get(path)
        after = roundtrip_sheets.get(path)
        if before is None or after is None:
            worksheet_diffs.append(
                {
                    "path": path,
                    "title_before": None if before is None else before.title,
                    "title_after": None if after is None else after.title,
                    "status": "removed" if after is None else "added",
                }
            )
            continue

        before_data = asdict(before)
        after_data = asdict(after)
        field_changes = diff_dict_values(
            before_data,
            after_data,
            [
                "title",
                "dimension",
                "row_count",
                "cell_count",
                "formula_count",
                "merged_range_count",
                "hyperlink_count",
                "table_count",
                "drawing_refs",
                "comment_ref_count",
                "legacy_drawing_count",
            ],
        )
        if field_changes:
            worksheet_diffs.append({"path": path, "status": "changed", "changes": field_changes})

    removed_risky_entries = [
        name
        for name in removed_entries
        if original_entries[name].category
        in {
            "macro",
            "media",
            "drawing",
            "comment",
            "pivot_cache",
            "pivot_table",
            "external_link",
            "embedding",
            "printer_settings",
            "control_property",
            "chart",
            "custom_xml",
        }
    ]

    largest_removed_entries = sorted(
        (
            {
                "name": name,
                "category": original_entries[name].category,
                "file_size": original_entries[name].file_size,
            }
            for name in removed_entries
        ),
        key=lambda item: item["file_size"],
        reverse=True,
    )[:20]

    largest_changed_entries = sorted(
        (
            {
                "name": name,
                "category": original_entries[name].category,
                "before_size": original_entries[name].file_size,
                "after_size": roundtrip_entries[name].file_size,
            }
            for name in changed_entries
        ),
        key=lambda item: abs(item["before_size"] - item["after_size"]),
        reverse=True,
    )[:20]

    return {
        "original": {
            "path": original["path"],
            "file_size": original["file_size"],
            "entry_count": len(original_entries),
            "category_counts": original["category_counts"],
        },
        "roundtrip": {
            "path": roundtrip["path"],
            "file_size": roundtrip["file_size"],
            "entry_count": len(roundtrip_entries),
            "category_counts": roundtrip["category_counts"],
        },
        "diff": {
            "removed_entries": removed_entries,
            "added_entries": added_entries,
            "changed_entries": changed_entries,
            "removed_by_category": dict(removed_by_category),
            "added_by_category": dict(added_by_category),
            "changed_by_category": dict(changed_by_category),
            "removed_risky_entries": removed_risky_entries,
            "largest_removed_entries": largest_removed_entries,
            "largest_changed_entries": largest_changed_entries,
            "worksheet_diffs": worksheet_diffs,
        },
    }


def format_report(report: dict[str, Any]) -> str:
    original = report["original"]
    roundtrip = report["roundtrip"]
    diff = report["diff"]

    lines = [
        "Excel Roundtrip Safety Assessment",
        f"Original:  {original['path']}",
        f"Roundtrip: {roundtrip['path']}",
        "",
        f"File size: {original['file_size']} -> {roundtrip['file_size']} bytes",
        f"Zip entries: {original['entry_count']} -> {roundtrip['entry_count']}",
        "",
        "Category counts:",
    ]

    all_categories = sorted(set(original["category_counts"]) | set(roundtrip["category_counts"]))
    for category in all_categories:
        before = original["category_counts"].get(category, 0)
        after = roundtrip["category_counts"].get(category, 0)
        marker = "" if before == after else "  CHANGED"
        lines.append(f"  - {category}: {before} -> {after}{marker}")

    if diff["removed_risky_entries"]:
        lines.extend(["", "High-risk removed parts:"])
        for name in diff["removed_risky_entries"]:
            lines.append(f"  - {name}")

    if diff["largest_removed_entries"]:
        lines.extend(["", "Largest removed parts:"])
        for item in diff["largest_removed_entries"][:10]:
            lines.append(f"  - {item['name']} [{item['category']}] {item['file_size']} bytes")

    if diff["largest_changed_entries"]:
        lines.extend(["", "Largest changed parts:"])
        for item in diff["largest_changed_entries"][:10]:
            lines.append(
                f"  - {item['name']} [{item['category']}] "
                f"{item['before_size']} -> {item['after_size']} bytes"
            )

    if diff["worksheet_diffs"]:
        lines.extend(["", "Worksheet structural changes:"])
        for item in diff["worksheet_diffs"]:
            if item["status"] != "changed":
                lines.append(
                    f"  - {item['path']}: {item['status']} "
                    f"(before={item.get('title_before')}, after={item.get('title_after')})"
                )
                continue
            lines.append(f"  - {item['path']}:")
            for field, values in item["changes"].items():
                lines.append(f"      {field}: {values['before']} -> {values['after']}")

    if not diff["removed_entries"] and not diff["added_entries"] and not diff["worksheet_diffs"]:
        lines.extend(["", "No structural differences detected at the ZIP/workbook level."])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assess structural differences between an original Excel workbook and a round-tripped workbook."
    )
    parser.add_argument("original", help="Path to the original workbook.")
    parser.add_argument("roundtrip", help="Path to the round-tripped workbook.")
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    args = parser.parse_args()

    original_path = Path(args.original).expanduser().resolve()
    roundtrip_path = Path(args.roundtrip).expanduser().resolve()

    if not original_path.is_file():
        raise FileNotFoundError(f"Original workbook not found: {original_path}")
    if not roundtrip_path.is_file():
        raise FileNotFoundError(f"Roundtrip workbook not found: {roundtrip_path}")

    report = build_report(original_path, roundtrip_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print(format_report(report))


if __name__ == "__main__":
    main()
