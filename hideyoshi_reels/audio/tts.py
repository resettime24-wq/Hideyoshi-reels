"""ナレーション音声合成（TTS）プロバイダ。

新しい音声APIを追加する場合は TTSProvider を継承し、create_tts() に登録してください。
"""

from __future__ import annotations

import logging
import random
import re
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from .wav import SAMPLE_RATE, write_wav

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    name = "base"
    credit: str | None = None  # キャプションに記載が必要なクレジット

    @abstractmethod
    def synthesize(self, text: str, out_path: Path) -> Path:
        """text を読み上げた音声ファイルを out_path に保存して返す。"""


class OpenAITTS(TTSProvider):
    name = "openai"
    credit = None
    INSTRUCTIONS = (
        "日本語で話してください。かわいいちびキャラの戦国武将として、明るく親しみやすく、"
        "少し低めで力強い声。受験生を励ますように、聞き取りやすくテンポよく話してください。"
    )

    def __init__(self, api_key: str, model: str, voice: str):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, max_retries=3, timeout=120)
        self.model, self.voice = model, voice

    def synthesize(self, text, out_path):
        kwargs = {"model": self.model, "voice": self.voice, "input": text, "response_format": "wav"}
        if "tts-1" not in self.model:
            kwargs["instructions"] = self.INSTRUCTIONS
        with self.client.audio.speech.with_streaming_response.create(**kwargs) as response:
            response.stream_to_file(out_path)
        return out_path


class VoicevoxTTS(TTSProvider):
    """VOICEVOX ENGINE（無料・ローカル/Docker で起動）。利用時はクレジット表記が必要です。"""

    name = "voicevox"

    def __init__(self, base_url: str, speaker: int, credit: str, speed: float = 1.1):
        self.base_url, self.speaker, self.credit, self.speed = base_url, speaker, credit, speed

    def synthesize(self, text, out_path):
        import requests

        q = requests.post(f"{self.base_url}/audio_query", params={"text": text, "speaker": self.speaker}, timeout=60)
        q.raise_for_status()
        query = q.json()
        query["speedScale"] = self.speed
        query["intonationScale"] = 1.2
        r = requests.post(f"{self.base_url}/synthesis", params={"speaker": self.speaker}, json=query, timeout=120)
        r.raise_for_status()
        Path(out_path).write_bytes(r.content)
        return out_path


class MockTTS(TTSProvider):
    """APIキー無しで動作確認するためのテスト音声（ピコピコ音で文字数分の長さを再現）。"""

    name = "mock"
    CHARS_PER_SEC = 7.5

    def synthesize(self, text, out_path):
        rng = random.Random(hash(text) & 0xFFFF)
        chunks = []
        for ch in text:
            if re.match(r"[、，,]", ch):
                chunks.append(np.zeros(int(SAMPLE_RATE * 0.18)))
                continue
            if re.match(r"[。！？!?…]", ch):
                chunks.append(np.zeros(int(SAMPLE_RATE * 0.3)))
                continue
            dur = 1.0 / self.CHARS_PER_SEC
            n = int(SAMPLE_RATE * dur)
            t = np.arange(n) / SAMPLE_RATE
            f0 = rng.uniform(170, 240)
            tone = sum(np.sin(2 * np.pi * f0 * h * t) / h for h in (1, 2, 3, 4))
            env = np.minimum(1, t / 0.015) * np.minimum(1, (dur - t) / 0.03)
            chunks.append(0.18 * tone * env)
        audio = np.concatenate(chunks) if chunks else np.zeros(SAMPLE_RATE)
        write_wav(out_path, audio)
        return out_path


def create_tts(settings) -> TTSProvider:
    provider = settings.resolved_tts_provider()
    if provider == "openai":
        return OpenAITTS(settings.openai_api_key, settings.openai_tts_model, settings.openai_tts_voice)
    if provider == "voicevox":
        return VoicevoxTTS(settings.voicevox_url, settings.voicevox_speaker, settings.voicevox_credit)
    return MockTTS()
