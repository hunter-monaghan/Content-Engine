from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
import xml.etree.ElementTree as ET

import httpx

from content_engine.config import Settings
from content_engine.models import TrendIdea


USER_AGENT = "ContentEngine/0.1 (+https://local.dev)"


@dataclass(slots=True)
class TrendProvider:
    name: str

    def fetch(self, niche: str, limit: int) -> list[TrendIdea]:
        raise NotImplementedError


class RedditTrendProvider(TrendProvider):
    def __init__(self) -> None:
        super().__init__(name="reddit")
        self.subreddits = ["AskReddit", "stories", "TrueOffMyChest"]

    def fetch(self, niche: str, limit: int) -> list[TrendIdea]:
        ideas: list[TrendIdea] = []
        headers = {"User-Agent": USER_AGENT}
        with httpx.Client(timeout=20.0, headers=headers) as client:
            for subreddit in self.subreddits:
                if len(ideas) >= limit:
                    break
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
                try:
                    response = client.get(url)
                    response.raise_for_status()
                except httpx.HTTPError:
                    continue
                payload = response.json()
                for child in payload.get("data", {}).get("children", []):
                    data = child.get("data", {})
                    title = str(data.get("title", "")).strip()
                    if not title:
                        continue
                    summary = data.get("selftext", "")[:280]
                    ideas.append(
                        TrendIdea(
                            source=f"reddit:r/{subreddit}",
                            title=title,
                            summary=summary or title,
                            url=f"https://reddit.com{data.get('permalink', '')}",
                            score_seed=float(data.get("ups", 0)) / 1000.0,
                            emotional_triggers=_extract_emotional_triggers(
                                f"{title} {summary}"
                            ),
                            keywords=_keywords_from_text(f"{title} {summary}", niche),
                            created_at=datetime.now(timezone.utc),
                        )
                    )
                    if len(ideas) >= limit:
                        break
        return ideas


class NewsTrendProvider(TrendProvider):
    def __init__(self, settings: Settings) -> None:
        super().__init__(name="news")
        self.api_key = settings.news_api_key

    def fetch(self, niche: str, limit: int) -> list[TrendIdea]:
        if not self.api_key:
            return []
        with httpx.Client(timeout=20.0) as client:
            try:
                response = client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={"apiKey": self.api_key, "pageSize": limit, "language": "en"},
                )
                response.raise_for_status()
            except httpx.HTTPError:
                return []
        ideas: list[TrendIdea] = []
        for article in response.json().get("articles", []):
            title = str(article.get("title", "")).strip()
            description = str(article.get("description", "")).strip()
            if not title:
                continue
            ideas.append(
                TrendIdea(
                    source="news",
                    title=title,
                    summary=description or title,
                    url=article.get("url", ""),
                    score_seed=0.7,
                    emotional_triggers=_extract_emotional_triggers(
                        f"{title} {description}"
                    ),
                    keywords=_keywords_from_text(f"{title} {description}", niche),
                )
            )
        return ideas


class GoogleNewsRssTrendProvider(TrendProvider):
    def __init__(self) -> None:
        super().__init__(name="google-news-rss")

    def fetch(self, niche: str, limit: int) -> list[TrendIdea]:
        params = {
            "q": niche,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
        with httpx.Client(timeout=20.0, headers={"User-Agent": USER_AGENT}) as client:
            try:
                response = client.get("https://news.google.com/rss/search", params=params)
                response.raise_for_status()
            except httpx.HTTPError:
                return []

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            return []

        ideas: list[TrendIdea] = []
        for item in root.findall("./channel/item")[:limit]:
            title = str(item.findtext("title", default="")).strip()
            link = str(item.findtext("link", default="")).strip()
            description = str(item.findtext("description", default="")).strip()
            if not title:
                continue
            ideas.append(
                TrendIdea(
                    source="google-news-rss",
                    title=title,
                    summary=description or title,
                    url=link,
                    score_seed=0.58,
                    emotional_triggers=_extract_emotional_triggers(f"{title} {description}"),
                    keywords=_keywords_from_text(f"{title} {description}", niche),
                )
            )
        return ideas


class TikTokTrendProvider(TrendProvider):
    def __init__(self, settings: Settings) -> None:
        super().__init__(name="tiktok")
        self.endpoint = settings.tiktok_trend_endpoint
        self.api_key = settings.tiktok_trend_api_key

    def fetch(self, niche: str, limit: int) -> list[TrendIdea]:
        if not self.endpoint:
            return []
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        with httpx.Client(timeout=20.0, headers=headers) as client:
            try:
                response = client.get(self.endpoint, params={"limit": limit, "niche": niche})
                response.raise_for_status()
            except httpx.HTTPError:
                return []
        ideas: list[TrendIdea] = []
        items = response.json().get("items", [])
        for item in items[:limit]:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            summary = str(item.get("summary", "")).strip() or title
            ideas.append(
                TrendIdea(
                    source="tiktok",
                    title=title,
                    summary=summary,
                    url=item.get("url", ""),
                    score_seed=float(item.get("engagement_score", 0.8)),
                    emotional_triggers=_extract_emotional_triggers(
                        f"{title} {summary}"
                    ),
                    keywords=_keywords_from_text(f"{title} {summary}", niche),
                )
            )
        return ideas


class MockTrendProvider(TrendProvider):
    def __init__(self) -> None:
        super().__init__(name="mock")

    def fetch(self, niche: str, limit: int) -> list[TrendIdea]:
        seeds = [
            (
                "A roommate hid a secret note in the freezer for 3 years",
                "Unexpected confession stories that pay off with a shocking reveal.",
            ),
            (
                "The side hustle that accidentally exposed a family secret",
                "High emotion, betrayal, and a satisfying twist.",
            ),
            (
                "Why everyone is talking about the five-minute rule at work",
                "A topical productivity idea that can be turned into a punchy explainer.",
            ),
        ]
        ideas = []
        for title, summary in seeds[:limit]:
            ideas.append(
                TrendIdea(
                    source="mock",
                    title=title,
                    summary=summary,
                    url="https://example.com/mock-trend",
                    score_seed=0.65,
                    emotional_triggers=_extract_emotional_triggers(
                        f"{title} {summary}"
                    ),
                    keywords=_keywords_from_text(f"{title} {summary}", niche),
                )
            )
        return ideas


def build_trend_providers(settings: Settings) -> list[TrendProvider]:
    providers: list[TrendProvider] = [RedditTrendProvider(), GoogleNewsRssTrendProvider()]
    if settings.tiktok_trend_endpoint:
        providers.insert(0, TikTokTrendProvider(settings))
    if not settings.free_mode and settings.news_api_key:
        providers.append(NewsTrendProvider(settings))
    providers.append(MockTrendProvider())
    return providers


def _extract_emotional_triggers(text: str) -> list[str]:
    lower = text.lower()
    mapping = {
        "shock": ["secret", "shocking", "exposed", "caught"],
        "curiosity": ["why", "what happened", "hidden", "note"],
        "conflict": ["fight", "betrayal", "roommate", "family"],
        "aspiration": ["rule", "hack", "side hustle", "career"],
    }
    matches = [name for name, needles in mapping.items() if any(n in lower for n in needles)]
    return matches or ["curiosity"]


def _keywords_from_text(text: str, niche: str) -> list[str]:
    tokens = [
        word.strip(".,!?\"'():;").lower()
        for word in text.split()
        if len(word.strip(".,!?\"'():;")) > 3
    ]
    seen = {niche.lower()}
    keywords = [niche.lower()]
    for token in tokens:
        if token not in seen:
            seen.add(token)
            keywords.append(token)
        if len(keywords) == 8:
            break
    return keywords


def flatten_ideas(provider_results: Iterable[list[TrendIdea]]) -> list[TrendIdea]:
    ideas: list[TrendIdea] = []
    seen: set[str] = set()
    for batch in provider_results:
        for idea in batch:
            key = f"{idea.source}:{idea.title.lower()}"
            if key in seen:
                continue
            seen.add(key)
            ideas.append(idea)
    return ideas
