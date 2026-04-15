from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET

from src.workflow.excel_update.schemas import ExcelUpdateChange, ExcelUpdateRequest

SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_NS = {"main": SPREADSHEET_NS, "rel": OFFICE_REL_NS, "pkgrel": PACKAGE_REL_NS}

ET.register_namespace("", SPREADSHEET_NS)
ET.register_namespace("r", OFFICE_REL_NS)


def resolve_output_path(request: ExcelUpdateRequest) -> str:
    if request.output_path:
        return request.output_path

    source = Path(request.excel_path)
    if source.suffix:
        return str(source.with_name(f"{source.stem}_updated{source.suffix}"))
    return f"{request.excel_path}_updated"


def export_updated_workbook(
    request: ExcelUpdateRequest,
    parsed_template: dict,
    changes: list[ExcelUpdateChange],
    output_path: str,
) -> str:
    source = Path(request.excel_path)
    if not source.is_file():
        raise FileNotFoundError(f"Excel file not found: {request.excel_path}")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if not changes:
        target.write_bytes(source.read_bytes())
        return str(target)

    worksheet_path = _resolve_worksheet_xml_path(source, parsed_template["sheet_name"])
    updated_xml = _build_updated_worksheet_xml(
        source,
        worksheet_path,
        parsed_template["target_column_index"],
        changes,
    )

    with ZipFile(source) as source_archive, ZipFile(target, "w") as target_archive:
        for info in source_archive.infolist():
            payload = updated_xml if info.filename == worksheet_path else source_archive.read(info.filename)
            compression = info.compress_type if info.compress_type is not None else ZIP_DEFLATED
            target_archive.writestr(info.filename, payload, compress_type=compression)

    return str(target)


def _resolve_worksheet_xml_path(excel_path: Path, sheet_name: str) -> str:
    with ZipFile(excel_path) as archive:
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        workbook_rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))

    rel_map: dict[str, str] = {}
    for node in workbook_rels_root.findall("pkgrel:Relationship", XML_NS):
        rel_id = node.attrib.get("Id")
        target = node.attrib.get("Target")
        if rel_id and target:
            rel_map[rel_id] = target

    for node in workbook_root.findall("main:sheets/main:sheet", XML_NS):
        if node.attrib.get("name") != sheet_name:
            continue
        rel_id = node.attrib.get(f"{{{OFFICE_REL_NS}}}id")
        if not rel_id or rel_id not in rel_map:
            break
        return _normalize_relationship_target("xl/workbook.xml", rel_map[rel_id])

    raise ValueError(f"Sheet XML path not found for sheet: {sheet_name}")


def _normalize_relationship_target(base_path: str, target: str) -> str:
    base = PurePosixPath(base_path).parent
    parts: list[str] = []
    for part in (base / target).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return PurePosixPath(*parts).as_posix()


def _build_updated_worksheet_xml(
    excel_path: Path,
    worksheet_path: str,
    target_column_index: int,
    changes: list[ExcelUpdateChange],
) -> bytes:
    with ZipFile(excel_path) as archive:
        worksheet_root = ET.fromstring(archive.read(worksheet_path))

    sheet_data = worksheet_root.find("main:sheetData", XML_NS)
    if sheet_data is None:
        raise ValueError(f"sheetData not found in worksheet: {worksheet_path}")

    row_map = {
        int(row.attrib["r"]): row
        for row in sheet_data.findall("main:row", XML_NS)
        if row.attrib.get("r")
    }

    for change in changes:
        row = row_map.get(change.row_index)
        if row is None:
            row = ET.Element(f"{{{SPREADSHEET_NS}}}row", {"r": str(change.row_index)})
            _insert_row(sheet_data, row, change.row_index)
            row_map[change.row_index] = row

        cell_ref = f"{_column_letter(target_column_index)}{change.row_index}"
        cell = _find_cell(row, cell_ref)
        if cell is None:
            cell = ET.Element(f"{{{SPREADSHEET_NS}}}c", {"r": cell_ref})
            _insert_cell(row, cell, cell_ref)

        _write_cell_value(cell, change.new_value)

    return ET.tostring(worksheet_root, encoding="utf-8", xml_declaration=True)


def _insert_row(sheet_data: ET.Element, new_row: ET.Element, row_index: int) -> None:
    inserted = False
    for idx, row in enumerate(list(sheet_data)):
        existing_row = int(row.attrib.get("r", "0"))
        if existing_row > row_index:
            sheet_data.insert(idx, new_row)
            inserted = True
            break
    if not inserted:
        sheet_data.append(new_row)


def _find_cell(row: ET.Element, cell_ref: str) -> ET.Element | None:
    for cell in row.findall("main:c", XML_NS):
        if cell.attrib.get("r") == cell_ref:
            return cell
    return None


def _insert_cell(row: ET.Element, new_cell: ET.Element, cell_ref: str) -> None:
    target_index = _cell_reference_sort_key(cell_ref)
    inserted = False
    cells = row.findall("main:c", XML_NS)
    for idx, cell in enumerate(cells):
        existing_ref = cell.attrib.get("r")
        if existing_ref and _cell_reference_sort_key(existing_ref) > target_index:
            row.insert(list(row).index(cell), new_cell)
            inserted = True
            break
    if not inserted:
        row.append(new_cell)


def _cell_reference_sort_key(cell_ref: str) -> tuple[int, int]:
    column = ""
    row = ""
    for char in cell_ref:
        if char.isalpha():
            column += char
        elif char.isdigit():
            row += char
    return (_column_index(column), int(row or "0"))


def _column_letter(column_index: int) -> str:
    result = ""
    current = column_index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _column_index(column_letters: str) -> int:
    value = 0
    for char in column_letters.upper():
        value = value * 26 + (ord(char) - 64)
    return value


def _write_cell_value(cell: ET.Element, value: object) -> None:
    for child in list(cell):
        if child.tag in {
            f"{{{SPREADSHEET_NS}}}v",
            f"{{{SPREADSHEET_NS}}}is",
            f"{{{SPREADSHEET_NS}}}f",
        }:
            cell.remove(child)

    if value is None:
        cell.attrib.pop("t", None)
        return

    if isinstance(value, bool):
        cell.attrib["t"] = "b"
        ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}v").text = "1" if value else "0"
        return

    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        cell.attrib.pop("t", None)
        ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}v").text = _format_number(value)
        return

    if isinstance(value, (datetime, date, time)):
        text = value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    else:
        text = str(value)

    cell.attrib["t"] = "inlineStr"
    inline = ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}is")
    text_node = ET.SubElement(inline, f"{{{SPREADSHEET_NS}}}t")
    if text != text.strip():
        text_node.attrib["{http://www.w3.org/XML/1998/namespace}space"] = "preserve"
    text_node.text = text


def _format_number(value: int | float | Decimal) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, int):
        return str(value)
    if value.is_integer():
        return str(int(value))
    return repr(value)
