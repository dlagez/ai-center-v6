from pathlib import Path

from openpyxl import Workbook, load_workbook

from src.workflow.excel_update.schemas import ExcelUpdateRequest
from src.workflow.excel_update.service import ExcelUpdateService


def _build_sample_excel(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "qingqian"
    worksheet.append(["项目编号", "项目名称", "3月实际产值"])
    worksheet.append(["HKZC-N-YW-2021-001", "项目A", None])
    worksheet.append(["HKZC-N-YW-2021-002", "项目B", 5])
    worksheet.append(["HKZC-N-YW-2021-003", "项目C", None])
    workbook.save(path)


def test_excel_update_service_writes_value_to_target_column(tmp_path) -> None:
    excel_path = tmp_path / "source.xlsx"
    output_path = tmp_path / "updated.xlsx"
    _build_sample_excel(excel_path)

    request = ExcelUpdateRequest(
        excel_path=str(excel_path),
        sheet_name="qingqian",
        match_column="项目编号",
        match_field="project_no",
        target_column="3月实际产值",
        output_path=str(output_path),
    )

    result = ExcelUpdateService().run(request)

    assert result.summary.total_records == 2
    assert result.summary.matched_records == 2
    assert result.summary.updated_cells == 2
    assert result.summary.error_count == 0

    workbook = load_workbook(output_path)
    worksheet = workbook["qingqian"]
    assert worksheet["C2"].value == 20
    assert worksheet["C3"].value == 30


def test_excel_update_service_collects_unmatched_keys(tmp_path) -> None:
    excel_path = tmp_path / "source.xlsx"
    output_path = tmp_path / "updated.xlsx"
    _build_sample_excel(excel_path)

    def custom_fetcher(_: ExcelUpdateRequest) -> list[dict[str, object]]:
        return [
            {"project_no": "HKZC-N-YW-2021-001", "value": 20},
            {"project_no": "HKZC-N-YW-2021-999", "value": 30},
        ]

    request = ExcelUpdateRequest(
        excel_path=str(excel_path),
        sheet_name="qingqian",
        match_column="项目编号",
        match_field="project_no",
        target_column="3月实际产值",
        output_path=str(output_path),
    )

    result = ExcelUpdateService(fetcher=custom_fetcher).run(request)

    assert result.unmatched_keys == ["HKZC-N-YW-2021-999"]
    assert result.summary.total_records == 2
    assert result.summary.matched_records == 1
    assert result.summary.unmatched_records == 1


def test_excel_update_service_supports_multiline_target_header(tmp_path) -> None:
    excel_path = tmp_path / "source_multiline.xlsx"
    output_path = tmp_path / "updated_multiline.xlsx"

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "qingqian"
    worksheet.append(["说明", "", "", ""])
    worksheet.append(["序号", "项目编号", "项目名称", "2026年回款、债权"])
    worksheet.append(["", "", "", "3月\n实际产值"])
    worksheet.append(["", "", "", ""])
    worksheet.append(["1", "HKZC-N-YW-2021-001", "项目A", None])
    worksheet.append(["2", "HKZC-N-YW-2021-002", "项目B", None])
    workbook.save(excel_path)

    request = ExcelUpdateRequest(
        excel_path=str(excel_path),
        sheet_name="qingqian",
        match_column="项目编号",
        match_field="project_no",
        target_column="3月实际产值",
        output_path=str(output_path),
    )

    result = ExcelUpdateService().run(request)

    assert result.summary.matched_records == 2
    assert result.summary.updated_cells == 2

    workbook = load_workbook(output_path)
    worksheet = workbook["qingqian"]
    assert worksheet["D5"].value == 20
    assert worksheet["D6"].value == 30
