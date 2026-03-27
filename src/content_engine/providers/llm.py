from __future__ import annotations

import json

import httpx

from content_engine.config import Settings
from content_engine.models import ScriptDraft, TrendIdea


SYSTEM_PROMPT = """
You write high-retention short-form video scripts for TikTok, YouTube Shorts, and Snapchat Spotlight.
Return valid JSON with keys: title, hook, build, payoff, full_script, duration_seconds, hook_variants.
Rules:
- 20 to 40 seconds total
- hook must grab attention in the first 2 seconds
- build tension quickly
- payoff should resolve with a twist, lesson, or reveal
- language should be natural and spoken
- optimize for loopability and retention
- keep hook_variants to short alternative openers
""".strip()


class ScriptGenerationProvider:
    def generate(self, idea: TrendIdea, niche: str, ab_hooks: int) -> ScriptDraft:
        raise NotImplementedError


class HeuristicScriptProvider(ScriptGenerationProvider):
    def generate(self, idea: TrendIdea, niche: str, ab_hooks: int) -> ScriptDraft:
        hook = f"You will not believe what happened right after {idea.title.lower()}."
        build = (
            f"Here is the setup: {idea.summary} Everyone thought they understood the story, "
            "but one small detail kept getting ignored."
        )
        payoff = (
            "Then the hidden detail flips everything, and suddenly the ending makes way more sense."
        )
        full_script = " ".join([hook, build, payoff])
        hook_variants = [
            hook,
            f"Wait until you hear the part nobody saw coming in this {niche} story.",
            f"This starts normal, then turns into the kind of twist people replay twice.",
            f"If this happened to you, you would never trust anyone the same way again.",
        ][: max(1, ab_hooks)]
        return ScriptDraft(
            title=idea.title[:90],
            hook=hook_variants[0],
            build=build,
            payoff=payoff,
            full_script=full_script,
            duration_seconds=30,
            hook_variants=hook_variants,
        )


class OpenAICompatibleScriptProvider(ScriptGenerationProvider):
    def __init__(self, settings: Settings) -> None:
        self.free_mode = settings.free_mode
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def generate(self, idea: TrendIdea, niche: str, ab_hooks: int) -> ScriptDraft:
        if self.free_mode or not self.api_key:
            return HeuristicScriptProvider().generate(idea, niche, ab_hooks)

        user_prompt = f"""
Niche: {niche}
Topic title: {idea.title}
Summary: {idea.summary}
Emotional triggers: {", ".join(idea.emotional_triggers)}
Keywords: {", ".join(idea.keywords)}
Generate {ab_hooks} hook variants.
""".strip()

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.9,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        with httpx.Client(timeout=45.0, headers=headers) as client:
            try:
                response = client.post(self.base_url, json=payload)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return ScriptDraft(
                    title=parsed["title"],
                    hook=parsed["hook"],
                    build=parsed["build"],
                    payoff=parsed["payoff"],
                    full_script=parsed["full_script"],
                    duration_seconds=int(parsed["duration_seconds"]),
                    hook_variants=list(parsed.get("hook_variants", []))[: max(1, ab_hooks)],
                )
            except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError):
                return HeuristicScriptProvider().generate(idea, niche, ab_hooks)
