from __future__ import annotations

from content_engine.models import TrendIdea, ViralScore
from content_engine.providers.trends import TrendProvider, flatten_ideas


class DiscoveryEngine:
    def __init__(self, providers: list[TrendProvider]) -> None:
        self.providers = providers

    def discover(self, niche: str, limit: int) -> list[TrendIdea]:
        provider_results = [provider.fetch(niche=niche, limit=limit) for provider in self.providers]
        return flatten_ideas(provider_results)

    def rank(self, ideas: list[TrendIdea]) -> list[tuple[TrendIdea, ViralScore]]:
        scored = [(idea, score_idea(idea)) for idea in ideas]
        return sorted(scored, key=lambda item: item[1].total, reverse=True)


def score_idea(idea: TrendIdea) -> ViralScore:
    trigger_bonus = min(len(idea.emotional_triggers) * 0.15, 0.45)
    hook_strength = min(0.45 + trigger_bonus + idea.score_seed * 0.2, 1.0)
    emotional_charge = min(0.4 + trigger_bonus + ("!" in idea.title) * 0.1, 1.0)
    freshness = min(0.5 + idea.score_seed * 0.4, 1.0)
    loopability = 0.85 if any(
        trigger in idea.emotional_triggers for trigger in ("shock", "curiosity", "conflict")
    ) else 0.62
    total = round((hook_strength * 0.35) + (emotional_charge * 0.3) + (freshness * 0.2) + (loopability * 0.15), 4)
    rationale = (
        f"Strong for short-form because it carries {', '.join(idea.emotional_triggers)} "
        f"and includes replayable tension around '{idea.title[:50]}'."
    )
    return ViralScore(
        total=total,
        hook_strength=round(hook_strength, 3),
        emotional_charge=round(emotional_charge, 3),
        freshness=round(freshness, 3),
        loopability=round(loopability, 3),
        rationale=rationale,
    )
