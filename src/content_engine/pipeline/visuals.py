from __future__ import annotations

import subprocess
from pathlib import Path

import httpx

from content_engine.config import Settings
from content_engine.models import ScriptDraft, TrendIdea, VisualAsset


class VisualSelector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def prepare(self, idea: TrendIdea, script: ScriptDraft, output_dir: Path) -> list[VisualAsset]:
        local_assets = self._local_backgrounds()
        if local_assets:
            return [VisualAsset(path=local_assets[0], source="local-assets", kind="video")]

        stock_asset = self._download_pexels_clip(idea, output_dir)
        if stock_asset:
            return [stock_asset]

        fallback = output_dir / "background.mp4"
        self._create_fallback_background(fallback, duration=script.duration_seconds)
        return [VisualAsset(path=fallback, source="generated", kind="video")]

    def _local_backgrounds(self) -> list[Path]:
        backgrounds_dir = self.settings.asset_dir / "backgrounds"
        if not backgrounds_dir.exists():
            return []
        return sorted(path for path in backgrounds_dir.iterdir() if path.suffix.lower() in {".mp4", ".mov"})

    def _download_pexels_clip(self, idea: TrendIdea, output_dir: Path) -> VisualAsset | None:
        if not self.settings.pexels_api_key:
            return None
        headers = {"Authorization": self.settings.pexels_api_key}
        query = idea.keywords[0] if idea.keywords else "city"
        with httpx.Client(timeout=30.0, headers=headers) as client:
            try:
                response = client.get(
                    "https://api.pexels.com/videos/search",
                    params={"query": query, "per_page": 1, "orientation": "portrait"},
                )
                response.raise_for_status()
            except httpx.HTTPError:
                return None
            videos = response.json().get("videos", [])
            if not videos:
                return None
            files = videos[0].get("video_files", [])
            link = next((item["link"] for item in files if item.get("height", 0) >= 1280), None)
            if not link:
                return None
            clip_path = output_dir / "stock.mp4"
            with client.stream("GET", link) as stream:
                stream.raise_for_status()
                with clip_path.open("wb") as file_handle:
                    for chunk in stream.iter_bytes():
                        file_handle.write(chunk)
        return VisualAsset(path=clip_path, source="pexels", kind="video")

    def _create_fallback_background(self, output_path: Path, duration: int) -> None:
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=#111827:s=1080x1920:r=30",
            "-vf",
            "format=yuv420p",
            "-t",
            str(duration),
            str(output_path),
        ]
        subprocess.run(command, check=True, capture_output=True)
