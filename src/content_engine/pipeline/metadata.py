from __future__ import annotations

from content_engine.models import CaptionPackage, ScriptDraft, TrendIdea, ViralScore


class MetadataGenerator:
    def generate(self, idea: TrendIdea, score: ViralScore, script: ScriptDraft, niche: str) -> CaptionPackage:
        title = _truncate(f"{script.hook_variants[0]} | {idea.title}", 90)
        hashtags = _hashtags(idea, niche)
        caption = (
            f"{script.hook_variants[0]} Watch to the end for the twist. "
            f"Score: {score.total:.2f}. {' '.join(hashtags)}"
        )
        return CaptionPackage(title=title, caption=caption, hashtags=hashtags)


def _hashtags(idea: TrendIdea, niche: str) -> list[str]:
    seeds = [f"#{niche.replace(' ', '')}", "#fyp", "#storytime", "#viral", "#shorts"]
    for keyword in idea.keywords[:4]:
        tag = "#" + "".join(ch for ch in keyword.title() if ch.isalnum())
        if tag.lower() not in {value.lower() for value in seeds}:
            seeds.append(tag)
    return seeds[:8]


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."
