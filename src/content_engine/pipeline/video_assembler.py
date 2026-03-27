from __future__ import annotations

import math
import subprocess
from pathlib import Path

from content_engine.config import Settings
from content_engine.models import ScriptDraft, VideoPackage, VisualAsset, VoiceAsset


class VideoAssembler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_subtitles(self, script: ScriptDraft, output_dir: Path) -> Path:
        subtitles_path = output_dir / "subtitles.srt"
        sentences = [segment.strip() for segment in script.full_script.split(".") if segment.strip()]
        if not sentences:
            sentences = [script.full_script]
        total_duration = max(script.duration_seconds, len(sentences) * 2)
        segment_duration = max(2, math.floor(total_duration / len(sentences)))
        lines = []
        start = 0
        for index, sentence in enumerate(sentences, start=1):
            end = min(total_duration, start + segment_duration)
            lines.append(str(index))
            lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
            lines.append(sentence + ".")
            lines.append("")
            start = end
        subtitles_path.write_text("\n".join(lines), encoding="utf-8")
        return subtitles_path

    def assemble(
        self,
        visuals: list[VisualAsset],
        voice: VoiceAsset,
        subtitles_path: Path,
        output_dir: Path,
    ) -> Path:
        if not visuals:
            raise ValueError("At least one visual asset is required.")
        visual = visuals[0]
        output_path = output_dir / "final.mp4"
        safe_subtitles = str(subtitles_path).replace("\\", "\\\\").replace(":", "\\:")
        filter_complex = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "subtitles="
            f"'{safe_subtitles}':force_style='FontName={self.settings.brand_font},"
            "FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,"
            "MarginV=120,Alignment=2'"
        )
        command = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(visual.path),
            "-i",
            str(voice.path),
            "-vf",
            filter_complex,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(output_path),
        ]
        subprocess.run(command, check=True, capture_output=True)
        return output_path


def _format_srt_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02},000"
