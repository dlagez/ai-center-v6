from pathlib import Path
from datetime import datetime

from fastapi.testclient import TestClient
from openpyxl import Workbook

from src.api.app import app
from src.workflow.excel_update.analyzer import analyze_excel_update


client = TestClient(app)


def _build_analysis_excel(path: Path) -> None:
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "封面"
    summary_sheet.append(["说明", "请勿修改"])

    worksheet = workbook.create_sheet("软件项目清欠表-收付现")
    worksheet.append(["说明", "", "", ""])
    worksheet.append(["序号", "项目编号", "项目名称", "2026年回款、债权"])
    worksheet.append(["", "", "", "3月\n实际产值"])
    worksheet.append(["", "", "", ""])
    worksheet.append(["1", "HKZC-N-YW-2021-001", "项目A", None])
    worksheet.append(["2", "HKZC-N-YW-2021-002", "项目B", None])
    workbook.save(path)


def test_excel_update_analysis_infers_sheet_and_target_column(tmp_path) -> None:
    excel_path = tmp_path / "analysis.xlsx"
    _build_analysis_excel(excel_path)

    result = analyze_excel_update(str(excel_path), "把这张清欠表 3 月实际产值更新一下")

    assert result.sheet_name == "软件项目清欠表-收付现"
    assert result.match_column == "项目编号"
    assert result.target_column == "3月实际产值"
    assert [item.model_dump(mode="json") for item in result.query_conditions] == [
        {"key": "month", "value": f"{datetime.now().year:04d}-03"},
        {"key": "metric", "value": "actual_output"},
    ]


def test_create_task_supports_prompt_only_parameters(tmp_path) -> None:
    excel_path = tmp_path / "analysis.xlsx"
    _build_analysis_excel(excel_path)

    with excel_path.open("rb") as file_obj:
        response = client.post(
            "/workflow/excel-update/tasks",
            files={"file": ("analysis.xlsx", file_obj, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"user_prompt": "把这张清欠表 3 月实际产值更新一下"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["sheet_name"] == "软件项目清欠表-收付现"
    assert payload["result"]["summary"]["updated_cells"] == 2


def test_excel_update_analysis_endpoint_returns_structure(tmp_path) -> None:
    excel_path = tmp_path / "analysis.xlsx"
    _build_analysis_excel(excel_path)

    with excel_path.open("rb") as file_obj:
        response = client.post(
            "/workflow/excel-update/analysis",
            files={"file": ("analysis.xlsx", file_obj, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"user_prompt": "把这张清欠表 3 月实际产值更新一下"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sheet_name"] == "软件项目清欠表-收付现"
    assert payload["match_column"] == "项目编号"
    assert payload["target_column"] == "3月实际产值"
