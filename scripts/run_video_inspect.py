import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.media.service import VideoInspectionService


def _load_prompt(args: argparse.Namespace) -> str | None:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8").strip()
    if args.prompt:
        return args.prompt.strip()
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a video by extracting one frame every N seconds and exporting an Excel report."
    )
    parser.add_argument("video_path", help="Local video path on the server.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=60,
        help="Extract one frame every N seconds. Default: 60.",
    )
    parser.add_argument(
        "--excel-path",
        default=None,
        help="Optional output Excel path. Default: <work_dir>/inspection.xlsx",
    )
    parser.add_argument(
        "--frames-dir",
        default=None,
        help="Optional directory to store extracted frames. Default: <work_dir>/frames",
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        default=True,
        help="Keep extracted frames on disk. Default: true.",
    )
    parser.add_argument(
        "--no-keep-frames",
        action="store_false",
        dest="keep_frames",
        help="Delete extracted frames after processing.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional vision model name.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Optional max tokens for the vision model.",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Optional custom prompt. If omitted, the built-in inspection prompt is used.",
    )
    parser.add_argument(
        "--prompt-file",
        default=None,
        help="Optional UTF-8 text file containing a custom prompt.",
    )
    args = parser.parse_args()

    if args.prompt and args.prompt_file:
        raise SystemExit("Use either --prompt or --prompt-file, not both.")

    prompt = _load_prompt(args)
    service = VideoInspectionService()

    def on_progress(current: int, total: int, frame_index: int, resumed: bool) -> None:
        status = "续跑跳过" if resumed else "已完成"
        print(f"当前处理到 {current} / {total} 帧 | frame_index={frame_index} | {status}")

    result = service.inspect_video(
        video_path=args.video_path,
        prompt=prompt,
        interval_seconds=args.interval_seconds,
        model=args.model,
        max_tokens=args.max_tokens,
        frames_dir=args.frames_dir,
        keep_frames=args.keep_frames,
        export_excel_path=args.excel_path,
        progress_callback=on_progress,
    ).model_dump()

    print(f"Work dir: {result.get('work_dir')}")
    print(f"Excel: {result.get('excel_path')}")
    print(f"Frames: {result.get('total_frames')}")
    print(f"Frames dir: {result.get('frames_dir')}")
    print(f"Checkpoint: {result.get('checkpoint_path')}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
