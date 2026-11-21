"""配置の自動検証: 安全領域からのはみ出し・文字同士の重なり・フォントに無い文字（文字欠け）。"""

from __future__ import annotations

from .canvas import TextBox
from .templates.base import REEL_RIGHT_UI, safe_area

TOLERANCE = 6  # px（フチ取りの誤差を許容）


def _intersect(a, b, tol=TOLERANCE) -> bool:
    return a[0] + tol < b[2] and b[0] + tol < a[2] and a[1] + tol < b[3] and b[1] + tol < a[3]


def check_layout(boxes: list[TextBox], post_format: str, size: tuple[int, int], fonts) -> list[str]:
    w, h = size
    issues = []
    sx0, sy0, sx1, sy1 = safe_area(post_format, w, h)
    k = w / 1080
    right_ui = tuple(int(v * k) for v in REEL_RIGHT_UI)
    text_boxes = [b for b in boxes if b.text.strip() and b.name != "watermark"]
    for b in text_boxes:
        x0, y0, x1, y1 = b.box
        if x0 < sx0 - TOLERANCE or y0 < sy0 - TOLERANCE or x1 > sx1 + TOLERANCE or y1 > sy1 + TOLERANCE:
            issues.append(f"安全領域の外: {b.name}「{b.text}」{b.box}")
        if post_format == "reel" and _intersect(b.box, right_ui):
            issues.append(f"右側のボタンと重なる可能性: {b.name}「{b.text}」{b.box}")
        if b.role:
            missing = fonts.missing_glyphs(b.text, b.role)
            if missing:
                issues.append(f"フォントに無い文字（文字欠け）: {''.join(sorted(missing))}（{b.name}）")
    for i, a in enumerate(text_boxes):
        for b in text_boxes[i + 1:]:
            if _intersect(a.box, b.box):
                issues.append(f"文字が重なっています: {a.name}「{a.text}」と {b.name}「{b.text}」")
    return issues
