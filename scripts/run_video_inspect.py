import argparse
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def _default_excel_path(video_path: str) -> str:
    video = Path(video_path)
    output_dir = ROOT / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(_unique_path(output_dir / f"{video.stem}_inspection.xlsx"))


def _default_frames_dir(video_path: str) -> str:
    video = Path(video_path)
    frames_dir = ROOT / "data" / "output" / "frames" / video.stem
    frames_dir.mkdir(parents=True, exist_ok=True)
    return str(frames_dir)


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
        help="Output Excel path. Default: write to a unique file under data/output/",
    )
    parser.add_argument(
        "--frames-dir",
        default=None,
        help="Optional directory to store extracted frames. Default: data/output/frames/<video_name>",
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="Keep extracted frames on disk. Default: false.",
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
    parser.add_argument("--host", default="127.0.0.1", help="API host.")
    parser.add_argument("--port", type=int, default=8000, help="API port.")
    args = parser.parse_args()

    if args.prompt and args.prompt_file:
        raise SystemExit("Use either --prompt or --prompt-file, not both.")

    excel_path = args.excel_path or _default_excel_path(args.video_path)
    frames_dir = args.frames_dir or _default_frames_dir(args.video_path)
    payload = {
        "video_path": args.video_path,
        "interval_seconds": args.interval_seconds,
        "export_excel_path": excel_path,
        "frames_dir": frames_dir,
        "keep_frames": args.keep_frames,
    }

    prompt = _load_prompt(args)
    if prompt:
        payload["prompt"] = prompt
    if args.model:
        payload["model"] = args.model
    if args.max_tokens is not None:
        payload["max_tokens"] = args.max_tokens

    response = requests.post(
        f"http://{args.host}:{args.port}/media/video/inspect",
        json=payload,
        timeout=600,
    )
    response.raise_for_status()
    result = response.json()

    print(f"Excel: {result.get('excel_path') or excel_path}")
    print(f"Frames: {result.get('total_frames')}")
    print(f"Frames dir: {result.get('frames_dir')}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
