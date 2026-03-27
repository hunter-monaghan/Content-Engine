from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time

from content_engine.config import Settings
from content_engine.models import VideoPackage
from content_engine.pipeline.analytics import AnalyticsTracker
from content_engine.pipeline.discovery import DiscoveryEngine
from content_engine.pipeline.metadata import MetadataGenerator
from content_engine.pipeline.posting import PostingQueue
from content_engine.pipeline.script_writer import ScriptWriter
from content_engine.pipeline.video_assembler import VideoAssembler
from content_engine.pipeline.visuals import VisualSelector
from content_engine.pipeline.voice import VoiceGenerator
from content_engine.providers.llm import OpenAICompatibleScriptProvider
from content_engine.providers.trends import build_trend_providers


class ContentEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.discovery = DiscoveryEngine(build_trend_providers(settings))
        self.script_writer = ScriptWriter(OpenAICompatibleScriptProvider(settings))
        self.voice_generator = VoiceGenerator.default(settings)
        self.visual_selector = VisualSelector(settings)
        self.video_assembler = VideoAssembler(settings)
        self.metadata_generator = MetadataGenerator()
        self.analytics = AnalyticsTracker(settings.output_dir / "analytics.jsonl")
        self.posting_queue = PostingQueue()

    def run_once(self, niche: str, limit: int, ab_hooks: int) -> list[VideoPackage]:
        ideas = self.discovery.discover(niche=niche, limit=max(limit * 3, 5))
        ranked = self.discovery.rank(ideas)[:limit]
        packages: list[VideoPackage] = []
        for index, (idea, score) in enumerate(ranked, start=1):
            output_dir = self._new_output_dir(niche=niche, index=index)
            script = self.script_writer.write(idea=idea, niche=niche, ab_hooks=ab_hooks)
            voice = self.voice_generator.generate(script=script, output_dir=output_dir)
            visuals = self.visual_selector.prepare(idea=idea, script=script, output_dir=output_dir)
            subtitles_path = self.video_assembler.create_subtitles(script=script, output_dir=output_dir)
            video_path = self.video_assembler.assemble(
                visuals=visuals,
                voice=voice,
                subtitles_path=subtitles_path,
                output_dir=output_dir,
            )
            captions = self.metadata_generator.generate(
                idea=idea,
                score=score,
                script=script,
                niche=niche,
            )

            package = VideoPackage(
                idea=idea,
                score=score,
                script=script,
                captions=captions,
                voice=voice,
                visuals=visuals,
                video_path=video_path,
                subtitles_path=subtitles_path,
                output_dir=output_dir,
                variant_id=output_dir.name,
            )
            self._write_package_files(package)
            self.analytics.record_package(package=package, niche=niche)
            self.posting_queue.enqueue(
                package=package,
                platforms=["tiktok", "youtube_shorts", "snapchat_spotlight"],
            )
            packages.append(package)
        return packages

    def run_schedule(self, niche: str, count: int, interval_minutes: int, ab_hooks: int) -> None:
        while True:
            self.run_once(niche=niche, limit=count, ab_hooks=ab_hooks)
            time.sleep(interval_minutes * 60)

    def _new_output_dir(self, niche: str, index: int) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        output_dir = self.settings.output_dir / f"{timestamp}_{niche}_{index:02d}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _write_package_files(self, package: VideoPackage) -> None:
        (package.output_dir / "script.txt").write_text(package.script.full_script, encoding="utf-8")
        caption_blob = "\n".join(
            [package.captions.title, "", package.captions.caption, "", " ".join(package.captions.hashtags)]
        )
        (package.output_dir / "caption.txt").write_text(caption_blob, encoding="utf-8")
        package.save_metadata()
