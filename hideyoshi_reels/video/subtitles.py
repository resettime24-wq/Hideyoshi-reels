"""字幕の分割・タイミング計算・SRT出力。"""

from __future__ import annotations

import re

from ..models import SubtitleCue

MAX_CHUNK = 26  # 1枚の字幕の最大文字数（2行 × 13文字程度）


def split_subtitle(text: str, max_chars: int = MAX_CHUNK) -> list[str]:
    """字幕を読みやすい長さに区切る（句読点優先）。"""
    text = text.strip()
    if not text:
        return []
    pieces = [p for p in re.split(r"(?<=[。！？!?])", text) if p.strip()]
    small: list[str] = []
    for p in pieces:
        if len(p) <= max_chars:
            small.append(p)
            continue
        parts = [x for x in re.split(r"(?<=[、，,])", p) if x]
        buf = ""
        for part in parts:
            while len(part) > max_chars:  # 句読点が無い長文は強制分割
                if buf:
                    small.append(buf)
                    buf = ""
                small.append(part[:max_chars])
                part = part[max_chars:]
            if len(buf) + len(part) <= max_chars:
                buf += part
            else:
                if buf:
                    small.append(buf)
                buf = part
        if buf:
            small.append(buf)
    # 短すぎる断片は前後とまとめる
    chunks: list[str] = []
    for s in small:
        if chunks and (len(s) < 8 or len(chunks[-1]) < 8) and len(chunks[-1]) + len(s) <= max_chars:
            chunks[-1] += s
        else:
            chunks.append(s)
    return [c.strip() for c in chunks if c.strip()]


def _weight(text: str) -> float:
    return max(1.0, len(re.sub(r"[、。！？!?，,…\s]", "", text)) + 0.4 * len(re.findall(r"[、。！？!?]", text)))


def time_cues(text: str, start: float, end: float) -> list[SubtitleCue]:
    """文字数に比例して、音声区間 [start, end] に字幕を割り当てる。"""
    chunks = split_subtitle(text)
    if not chunks:
        return []
    total = sum(_weight(c) for c in chunks)
    cues, t = [], start
    for i, c in enumerate(chunks):
        dur = (end - start) * _weight(c) / total
        cue_end = end if i == len(chunks) - 1 else t + dur
        cues.append(SubtitleCue(start=round(t, 3), end=round(cue_end, 3), text=c))
        t = cue_end
    return cues


def _fmt(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(cues: list[SubtitleCue]) -> str:
    blocks = [f"{i}\n{_fmt(c.start)} --> {_fmt(c.end)}\n{c.text}\n" for i, c in enumerate(cues, 1)]
    return "\n".join(blocks)
