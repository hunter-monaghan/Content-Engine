from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from content_engine.models import VideoPackage


@dataclass(slots=True)
class PostingJob:
    platform: str
    video_path: Path
    caption: str
    title: str
    variant_id: str


class PostingQueue:
    def __init__(self) -> None:
        self.jobs: list[PostingJob] = []

    def enqueue(self, package: VideoPackage, platforms: list[str]) -> list[PostingJob]:
        created = [
            PostingJob(
                platform=platform,
                video_path=package.video_path,
                caption=package.captions.caption,
                title=package.captions.title,
                variant_id=package.variant_id,
            )
            for platform in platforms
        ]
        self.jobs.extend(created)
        return created
