from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class TrendIdea:
    source: str
    title: str
    summary: str
    url: str
    score_seed: float
    emotional_triggers: list[str]
    keywords: list[str]
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class ViralScore:
    total: float
    hook_strength: float
    emotional_charge: float
    freshness: float
    loopability: float
    rationale: str


@dataclass(slots=True)
class ScriptDraft:
    title: str
    hook: str
    build: str
    payoff: str
    full_script: str
    duration_seconds: int
    hook_variants: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VoiceAsset:
    provider: str
    path: Path
    duration_seconds: float


@dataclass(slots=True)
class VisualAsset:
    path: Path
    source: str
    kind: str


@dataclass(slots=True)
class CaptionPackage:
    title: str
    caption: str
    hashtags: list[str]


@dataclass(slots=True)
class VideoPackage:
    idea: TrendIdea
    score: ViralScore
    script: ScriptDraft
    captions: CaptionPackage
    voice: VoiceAsset
    visuals: list[VisualAsset]
    video_path: Path
    subtitles_path: Path
    output_dir: Path
    variant_id: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["voice"]["path"] = str(self.voice.path)
        payload["video_path"] = str(self.video_path)
        payload["subtitles_path"] = str(self.subtitles_path)
        payload["output_dir"] = str(self.output_dir)
        payload["visuals"] = [
            {**asdict(visual), "path": str(visual.path)} for visual in self.visuals
        ]
        payload["idea"]["created_at"] = self.idea.created_at.isoformat()
        return payload

    def save_metadata(self) -> Path:
        metadata_path = self.output_dir / "metadata.json"
        metadata_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return metadata_path


@dataclass(slots=True)
class AnalyticsRecord:
    variant_id: str
    platform: str
    title: str
    caption: str
    niche: str
    source: str
    hook: str
    published_at: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    retention: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=True)
