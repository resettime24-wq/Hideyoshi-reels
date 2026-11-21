"""効果音とBGMをプログラムで合成する（外部素材を使わないので著作権フリー）。"""

from __future__ import annotations

import numpy as np

from .wav import SAMPLE_RATE

SR = SAMPLE_RATE


def _t(sec: float) -> np.ndarray:
    return np.arange(int(SR * sec)) / SR


def _env(t: np.ndarray, attack: float, decay: float) -> np.ndarray:
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def pop() -> np.ndarray:
    t = _t(0.15)
    freq = 900 * np.exp(-t * 18) + 300
    return 0.5 * np.sin(2 * np.pi * np.cumsum(freq) / SR) * _env(t, 0.003, 0.04)


def whoosh() -> np.ndarray:
    t = _t(0.45)
    rng = np.random.default_rng(1)
    noise = rng.standard_normal(len(t))
    kernel = np.ones(30) / 30
    smooth = np.convolve(noise, kernel, mode="same")
    env = np.sin(np.pi * t / t[-1]) ** 2
    return 0.9 * smooth * env


def ding() -> np.ndarray:
    t = _t(1.0)
    tone = np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 2637 * t) + 0.25 * np.sin(2 * np.pi * 3951 * t)
    return 0.3 * tone * _env(t, 0.002, 0.25)


def boing() -> np.ndarray:
    t = _t(0.5)
    freq = 220 + 120 * np.sin(2 * np.pi * 12 * t) * np.exp(-t * 4)
    return 0.45 * np.sin(2 * np.pi * np.cumsum(freq) / SR) * _env(t, 0.005, 0.18)


def drum() -> np.ndarray:
    """和太鼓風の「ドン」。"""
    t = _t(0.7)
    freq = 110 * np.exp(-t * 6) + 55
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * _env(t, 0.002, 0.18)
    rng = np.random.default_rng(2)
    hit = rng.standard_normal(len(t)) * _env(t, 0.001, 0.015) * 0.3
    return 0.9 * (body + hit)


def sparkle() -> np.ndarray:
    out = np.zeros(int(SR * 0.9))
    for i, f in enumerate([1568, 2093, 2637, 3136, 4186]):
        t = _t(0.4)
        tone = 0.18 * np.sin(2 * np.pi * f * t) * _env(t, 0.002, 0.09)
        start = int(SR * 0.08 * i)
        out[start:start + len(tone)] += tone[: len(out) - start]
    return out


SFX = {"pop": pop, "whoosh": whoosh, "ding": ding, "boing": boing, "drum": drum, "sparkle": sparkle}


def make_sfx(name: str) -> np.ndarray | None:
    fn = SFX.get(name)
    return fn() if fn else None


def make_bgm(duration: float, seed: int = 0) -> np.ndarray:
    """和風ペンタトニック（陽音階）の軽いアルペジオBGM。"""
    rng = np.random.default_rng(seed)
    bpm = 96
    step = 60 / bpm / 2  # 8分音符
    scale = [293.66, 329.63, 392.00, 440.00, 493.88, 587.33, 659.25]  # D E G A B D E
    n = int(SR * duration)
    out = np.zeros(n + SR)
    pattern = [0, 2, 4, 2, 5, 4, 2, 1]
    i = 0
    t_note = _t(step * 1.8)
    while i * step < duration:
        base = pattern[i % len(pattern)]
        if (i // 16) % 2 == 1:
            base = min(len(scale) - 1, base + 1)
        f = scale[base] * (0.5 if rng.random() < 0.15 else 1.0)
        pluck = (np.sin(2 * np.pi * f * t_note) + 0.3 * np.sin(2 * np.pi * 2 * f * t_note)) * _env(t_note, 0.004, 0.22)
        start = int(i * step * SR)
        out[start:start + len(pluck)] += 0.12 * pluck
        if i % 8 == 0:  # ベース
            tb = _t(step * 7)
            bass = np.sin(2 * np.pi * 73.42 * tb) * _env(tb, 0.01, 0.6)
            out[start:start + len(bass)] += 0.18 * bass[: len(out) - start]
        i += 1
    out = out[:n]
    fade = int(SR * 1.0)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out
