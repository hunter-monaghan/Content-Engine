from __future__ import annotations

from content_engine.config import Settings
from pathlib import Path

from content_engine.models import ScriptDraft, VoiceAsset
from content_engine.providers.tts import (
    ElevenLabsTTSProvider,
    EspeakTTSProvider,
    FallbackSilentTTSProvider,
    OpenAITTSProvider,
    TTSProvider,
)


class VoiceGenerator:
    def __init__(self, providers: list[TTSProvider]) -> None:
        self.providers = providers

    @classmethod
    def default(cls, settings: Settings) -> "VoiceGenerator":
        if settings.free_mode:
            return cls([EspeakTTSProvider(), FallbackSilentTTSProvider()])
        return cls(
            [
                ElevenLabsTTSProvider(settings),
                OpenAITTSProvider(settings),
                EspeakTTSProvider(),
                FallbackSilentTTSProvider(),
            ]
        )

    def generate(self, script: ScriptDraft, output_dir: Path) -> VoiceAsset:
        output_path = output_dir / "voice.mp3"
        errors: list[str] = []
        for provider in self.providers:
            try:
                return provider.synthesize(script.full_script, output_path)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{provider.__class__.__name__}: {exc}")
        raise RuntimeError("No TTS provider succeeded. " + "; ".join(errors))
