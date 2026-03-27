from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional during lightweight checks
    def load_dotenv() -> None:
        return None


load_dotenv()


@dataclass(slots=True)
class Settings:
    project_root: Path
    output_dir: Path
    asset_dir: Path
    default_niche: str
    videos_per_run: int
    brand_font: str
    openai_api_key: str | None
    openai_model: str
    openai_tts_model: str
    openai_tts_voice: str
    elevenlabs_api_key: str | None
    elevenlabs_voice_id: str | None
    news_api_key: str | None
    pexels_api_key: str | None
    tiktok_trend_endpoint: str | None
    tiktok_trend_api_key: str | None
    web_host: str
    web_port: int
    site_name: str
    public_generation_enabled: bool
    app_admin_token: str | None
    max_jobs_per_ip: int
    job_window_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        project_root = Path.cwd()
        output_dir = project_root / os.getenv("OUTPUT_DIR", "output")
        asset_dir = project_root / os.getenv("ASSET_DIR", "assets")
        output_dir.mkdir(parents=True, exist_ok=True)
        asset_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            project_root=project_root,
            output_dir=output_dir,
            asset_dir=asset_dir,
            default_niche=os.getenv("DEFAULT_NICHE", "storytime"),
            videos_per_run=int(os.getenv("VIDEOS_PER_RUN", "3")),
            brand_font=os.getenv("BRAND_FONT", "Arial"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
            news_api_key=os.getenv("NEWS_API_KEY"),
            pexels_api_key=os.getenv("PEXELS_API_KEY"),
            tiktok_trend_endpoint=os.getenv("TIKTOK_TREND_ENDPOINT"),
            tiktok_trend_api_key=os.getenv("TIKTOK_TREND_API_KEY"),
            web_host=os.getenv("WEB_HOST", "127.0.0.1"),
            web_port=int(os.getenv("PORT", os.getenv("WEB_PORT", "8000"))),
            site_name=os.getenv("SITE_NAME", "Content Engine"),
            public_generation_enabled=_env_bool("PUBLIC_GENERATION_ENABLED", True),
            app_admin_token=os.getenv("APP_ADMIN_TOKEN"),
            max_jobs_per_ip=int(os.getenv("MAX_JOBS_PER_IP", "3")),
            job_window_seconds=int(os.getenv("JOB_WINDOW_SECONDS", "900")),
        )


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
