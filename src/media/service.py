import shutil
from collections.abc import Callable

from src.media.excel import ExcelReportWriter
from src.media.prompts import resolve_inspection_prompt
from src.media.runtime import (
    build_work_paths,
    load_checkpoint,
    restore_frame_results,
    save_checkpoint,
    save_request_metadata,
)
from src.media.schemas import FrameInspectionResult, VideoInspectionResult
from src.media.video import extract_video_frames
from src.media.vision import inspect_image
from src.observability import observe


class VideoInspectionService:
    def inspect_video(
        self,
        *,
        video_path: str,
        prompt: str | None = None,
        interval_seconds: int = 60,
        model: str | None = None,
        max_tokens: int | None = None,
        match_field: str | None = None,
        frames_dir: str | None = None,
        keep_frames: bool = True,
        export_excel_path: str | None = None,
        progress_callback: Callable[[int, int, int, bool], None] | None = None,
    ) -> VideoInspectionResult:
        resolved_prompt = resolve_inspection_prompt(prompt)

        with observe(
            name="media.inspect_video",
            as_type="chain",
            input={
                "video_path": video_path,
                "interval_seconds": interval_seconds,
                "model": model,
                "match_field": match_field,
                "frames_dir": frames_dir,
                "keep_frames": keep_frames,
                "export_excel_path": export_excel_path,
                "prompt_source": "custom" if prompt and prompt.strip() else "default",
            },
        ):
            work_paths = build_work_paths(video_path)
            resolved_frames_dir_arg = frames_dir or str(work_paths["frames_dir"])
            resolved_excel_path = export_excel_path or str(work_paths["excel_path"])
            checkpoint_path = work_paths["checkpoint_path"]
            save_request_metadata(
                work_paths["request_path"],
                {
                    "video_path": video_path,
                    "interval_seconds": interval_seconds,
                    "model": model,
                    "match_field": match_field,
                    "frames_dir": resolved_frames_dir_arg,
                    "keep_frames": keep_frames,
                    "export_excel_path": resolved_excel_path,
                    "prompt_source": "custom" if prompt and prompt.strip() else "default",
                },
            )

            extracted_frames, resolved_frames_dir = extract_video_frames(
                video_path=video_path,
                interval_seconds=interval_seconds,
                frames_dir=resolved_frames_dir_arg,
            )

            checkpoint_data = load_checkpoint(checkpoint_path)
            frame_results = restore_frame_results(checkpoint_data)
            completed_by_index = {frame.frame_index: frame for frame in frame_results}
            excel_path: str | None = resolved_excel_path
            excel_writer: ExcelReportWriter | None = None
            try:
                excel_writer = ExcelReportWriter(
                    video_path=video_path,
                    interval_seconds=interval_seconds,
                    output_path=resolved_excel_path,
                )

                total_frames = len(extracted_frames)
                for current_index, frame in enumerate(extracted_frames, start=1):
                    existing = completed_by_index.get(frame.frame_index)
                    if existing is not None:
                        if progress_callback is not None:
                            progress_callback(current_index, total_frames, frame.frame_index, True)
                        continue

                    raw_answer, parsed_result = inspect_image(
                        prompt=resolved_prompt,
                        image_path=str(frame.frame_path),
                        model=model,
                        max_tokens=max_tokens,
                    )

                    is_match: bool | None = None
                    if match_field and parsed_result is not None:
                        candidate = parsed_result.get(match_field)
                        if isinstance(candidate, bool):
                            is_match = candidate

                    frame_result = FrameInspectionResult(
                        frame_index=frame.frame_index,
                        timestamp_seconds=frame.timestamp_seconds,
                        frame_path=str(frame.frame_path),
                        raw_answer=raw_answer,
                        parsed_result=parsed_result,
                        is_match=is_match,
                    )
                    frame_results.append(frame_result)
                    completed_by_index[frame.frame_index] = frame_result

                    excel_writer.append_frame(frame_result)
                    save_checkpoint(
                        checkpoint_path,
                        video_path=video_path,
                        interval_seconds=interval_seconds,
                        work_dir=str(work_paths["work_dir"]),
                        frames_dir=str(resolved_frames_dir),
                        excel_path=excel_path,
                        match_field=match_field,
                        frames=sorted(frame_results, key=lambda item: item.frame_index),
                    )
                    if progress_callback is not None:
                        progress_callback(current_index, total_frames, frame.frame_index, False)
            finally:
                if not keep_frames:
                    shutil.rmtree(resolved_frames_dir, ignore_errors=True)
                    for frame_result in frame_results:
                        frame_result.frame_path = None

            has_match: bool | None = None
            if match_field:
                has_match = any(frame.is_match is True for frame in frame_results)

            return VideoInspectionResult(
                video_path=video_path,
                interval_seconds=interval_seconds,
                total_frames=len(frame_results),
                match_field=match_field,
                has_match=has_match,
                frames_dir=str(resolved_frames_dir) if keep_frames else None,
                frames=sorted(frame_results, key=lambda item: item.frame_index),
                excel_path=excel_path,
                work_dir=str(work_paths["work_dir"]),
                checkpoint_path=str(checkpoint_path),
            )
