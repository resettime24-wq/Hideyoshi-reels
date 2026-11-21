"""WAV の読み書き（numpy）。"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from ..utils import run_cmd

SAMPLE_RATE = 44100


def write_wav(path: Path, audio: np.ndarray, sr: int = SAMPLE_RATE) -> Path:
    audio = np.clip(np.asarray(audio, dtype=np.float64), -1.0, 1.0)
    data = (audio * 32767).astype("<i2")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())
    return Path(path)


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == SAMPLE_RATE
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2")
    return data.astype(np.float64) / 32767


def normalize_audio(src: Path, dst: Path, tempo: float = 1.0) -> Path:
    """任意の音声を 44.1kHz モノラル WAV に変換（必要なら話速を変更・前後の無音をカット）。"""
    filters = ["silenceremove=start_periods=1:start_threshold=-50dB",
               "areverse", "silenceremove=start_periods=1:start_threshold=-50dB", "areverse"]
    if abs(tempo - 1.0) > 0.01:
        filters.append(f"atempo={tempo:.3f}")
    run_cmd(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", ",".join(filters),
             "-ac", "1", "-ar", str(SAMPLE_RATE), "-sample_fmt", "s16", str(dst)], "音声の変換")
    return dst
