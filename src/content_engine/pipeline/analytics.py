from __future__ import annotations

from pathlib import Path

from content_engine.models import AnalyticsRecord, VideoPackage


class AnalyticsTracker:
    def __init__(self, analytics_path: Path) -> None:
        self.analytics_path = analytics_path
        self.analytics_path.parent.mkdir(parents=True, exist_ok=True)

    def record_package(self, package: VideoPackage, niche: str, platform: str = "unpublished") -> None:
        record = AnalyticsRecord(
            variant_id=package.variant_id,
            platform=platform,
            title=package.captions.title,
            caption=package.captions.caption,
            niche=niche,
            source=package.idea.source,
            hook=package.script.hook,
            published_at="pending",
        )
        with self.analytics_path.open("a", encoding="utf-8") as file_handle:
            file_handle.write(record.to_json() + "\n")
