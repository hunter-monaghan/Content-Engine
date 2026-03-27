from __future__ import annotations

import subprocess
from pathlib import Path

import httpx

from content_engine.config import Settings
from content_engine.models import VoiceAsset


class TTSProvider:
    def synthesize(self, text: str, output_path: Path) -> VoiceAsset:
        raise NotImplementedError


class ElevenLabsTTSProvider(TTSProvider):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.elevenlabs_api_key
        self.voice_id = settings.elevenlabs_voice_id

    def synthesize(self, text: str, output_path: Path) -> VoiceAsset:
        if not self.api_key or not self.voice_id:
            raise RuntimeError("ElevenLabs is not configured.")
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8},
        }
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        with httpx.Client(timeout=90.0, headers=headers) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            output_path.write_bytes(response.content)
        return VoiceAsset(provider="elevenlabs", path=output_path, duration_seconds=30.0)


class OpenAITTSProvider(TTSProvider):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.openai_api_key
        self.model = settings.openai_tts_model
        self.voice = settings.openai_tts_voice

    def synthesize(self, text: str, output_path: Path) -> VoiceAsset:
        if not self.api_key:
            raise RuntimeError("OpenAI TTS is not configured.")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "voice": self.voice, "input": text}
        with httpx.Client(timeout=90.0, headers=headers) as client:
            response = client.post("https://api.openai.com/v1/audio/speech", json=payload)
            response.raise_for_status()
            output_path.write_bytes(response.content)
        return VoiceAsset(provider="openai", path=output_path, duration_seconds=30.0)


class FallbackSilentTTSProvider(TTSProvider):
    def synthesize(self, text: str, output_path: Path) -> VoiceAsset:
        duration = max(8, min(40, len(text.split()) // 2))
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            str(duration),
            "-q:a",
            "9",
            "-acodec",
            "libmp3lame",
            str(output_path),
        ]
        subprocess.run(command, check=True, capture_output=True)
        return VoiceAsset(provider="fallback", path=output_path, duration_seconds=float(duration))
