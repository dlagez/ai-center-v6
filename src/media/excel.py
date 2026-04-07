from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill

from src.media.schemas import VideoInspectionResult

REPORT_HEADERS = [
    "视频文件",
    "抽帧间隔(秒)",
    "帧序号",
    "时间点",
    "截图",
    "安全帽颜色",
    "反光衣颜色",
    "爆闪灯颜色",
    "是否为管理人员",
    "判定依据",
    "原始输出",
]


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _format_timestamp(seconds: int) -> str:
    hours, remain = divmod(seconds, 3600)
    minutes, secs = divmod(remain, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _apply_layout(worksheet) -> None:
    widths = {
        "A": 28,
        "B": 12,
        "C": 10,
        "D": 12,
        "E": 18,
        "F": 16,
        "G": 18,
        "H": 16,
        "I": 14,
        "J": 56,
        "K": 56,
    }
    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width

    header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")


def export_video_inspection_report(
    result: VideoInspectionResult,
    output_path: str,
) -> str:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "巡检结果"
    worksheet.append(REPORT_HEADERS)
    _apply_layout(worksheet)
    worksheet.freeze_panes = "A2"

    for row_index, frame in enumerate(result.frames, start=2):
        parsed = frame.parsed_result or {}
        worksheet.append(
            [
                result.video_path,
                result.interval_seconds,
                frame.frame_index,
                _format_timestamp(frame.timestamp_seconds),
                "",
                parsed.get("安全帽颜色", ""),
                parsed.get("反光衣颜色", ""),
                parsed.get("爆闪灯颜色", ""),
                parsed.get("是否为管理人员", ""),
                parsed.get("判定依据", ""),
                frame.raw_answer,
            ]
        )

        worksheet.row_dimensions[row_index].height = 96
        for column_index in range(1, len(REPORT_HEADERS) + 1):
            cell = worksheet.cell(row=row_index, column=column_index)
            cell.alignment = Alignment(vertical="top", wrap_text=True)

        if frame.frame_path and Path(frame.frame_path).is_file():
            image = XLImage(frame.frame_path)
            image.width = 120
            image.height = 90
            worksheet.add_image(image, f"E{row_index}")

    output = Path(output_path).expanduser()
    _ensure_parent(output)
    workbook.save(output)
    return str(output)
