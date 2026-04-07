import shutil

from src.media.excel import export_video_inspection_report
from src.media.prompts import resolve_inspection_prompt
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
        interval_seconds: int = 20,
        model: str | None = None,
        max_tokens: int | None = None,
        match_field: str | None = None,
        frames_dir: str | None = None,
        keep_frames: bool = True,
        export_excel_path: str | None = None,
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
            extracted_frames, resolved_frames_dir = extract_video_frames(
                video_path=video_path,
                interval_seconds=interval_seconds,
                frames_dir=frames_dir,
            )

            frame_results: list[FrameInspectionResult] = []
            excel_path: str | None = None
            try:
                for frame in extracted_frames:
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

                    frame_results.append(
                        FrameInspectionResult(
                            frame_index=frame.frame_index,
                            timestamp_seconds=frame.timestamp_seconds,
                            frame_path=str(frame.frame_path),
                            raw_answer=raw_answer,
                            parsed_result=parsed_result,
                            is_match=is_match,
                        )
                    )

                temp_result = VideoInspectionResult(
                    video_path=video_path,
                    interval_seconds=interval_seconds,
                    total_frames=len(frame_results),
                    match_field=match_field,
                    has_match=None,
                    frames_dir=str(resolved_frames_dir),
                    frames=frame_results,
                )
                if export_excel_path:
                    excel_path = export_video_inspection_report(
                        temp_result,
                        output_path=export_excel_path,
                    )
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
                frames=frame_results,
                excel_path=excel_path,
            )
