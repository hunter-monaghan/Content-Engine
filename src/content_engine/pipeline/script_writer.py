from __future__ import annotations

from content_engine.models import ScriptDraft, TrendIdea
from content_engine.providers.llm import ScriptGenerationProvider


class ScriptWriter:
    def __init__(self, provider: ScriptGenerationProvider) -> None:
        self.provider = provider

    def write(self, idea: TrendIdea, niche: str, ab_hooks: int) -> ScriptDraft:
        script = self.provider.generate(idea=idea, niche=niche, ab_hooks=ab_hooks)
        script.duration_seconds = max(20, min(40, script.duration_seconds))
        return script
