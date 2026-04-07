from pathlib import Path

from PIL import Image
from openpyxl import load_workbook

from src.media.excel import export_video_inspection_report
from src.media.schemas import VideoInspectionResult


def test_export_video_inspection_report_writes_required_columns(tmp_path) -> None:
    image_path = tmp_path / "frame.jpg"
    Image.new("RGB", (320, 180), color=(180, 220, 120)).save(image_path)

    report = VideoInspectionResult.model_validate(
        {
            "video_path": "D:/videos/demo.mp4",
            "interval_seconds": 20,
            "total_frames": 1,
            "frames_dir": str(tmp_path),
            "frames": [
                {
                    "frame_index": 0,
                    "timestamp_seconds": 0,
                    "frame_path": str(image_path),
                    "raw_answer": '{"安全帽颜色":"红色","反光衣颜色":"黄绿色","爆闪灯颜色":"无","是否为管理人员":"否","判定依据":"示例"}',
                    "parsed_result": {
                        "安全帽颜色": "红色",
                        "反光衣颜色": "黄绿色",
                        "爆闪灯颜色": "无",
                        "是否为管理人员": "否",
                        "判定依据": "示例",
                    },
                }
            ],
        }
    )

    output_path = tmp_path / "report.xlsx"
    saved_path = export_video_inspection_report(report, str(output_path))

    workbook = load_workbook(saved_path)
    worksheet = workbook["巡检结果"]

    assert worksheet["A1"].value == "视频文件"
    assert worksheet["F1"].value == "安全帽颜色"
    assert worksheet["J1"].value == "判定依据"
    assert worksheet["F2"].value == "红色"
    assert worksheet["G2"].value == "黄绿色"
    assert worksheet["H2"].value == "无"
    assert worksheet["I2"].value == "否"
    assert worksheet["J2"].value == "示例"
    assert len(worksheet._images) == 1
