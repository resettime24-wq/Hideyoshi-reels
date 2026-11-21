"""コマンドライン入口。

使い方:
  python -m hideyoshi_reels generate                     # 設定どおりに1投稿を制作（既定: リール）
  python -m hideyoshi_reels generate --format feed       # フィード画像（1080×1350）
  python -m hideyoshi_reels generate --format carousel   # カルーセル（複数枚）
  python -m hideyoshi_reels generate --design B          # デザインを手動指定（A/B/C/D/auto）
  python -m hideyoshi_reels generate --mock              # APIを使わず無料で試す
  python -m hideyoshi_reels preview                      # 同じテーマで A〜D を試作して比較
  python -m hideyoshi_reels check                        # 設定の確認
  python -m hideyoshi_reels history                      # 過去の企画一覧
"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import DESIGN_STYLES, POST_FORMATS, load_settings
from .history import History
from .utils import setup_logging


def _settings(args):
    overrides = {}
    if getattr(args, "mock", False):
        overrides["mode"] = "mock"
    if getattr(args, "format", None):
        overrides["post_format"] = args.format
    if getattr(args, "design", None):
        overrides["design_style"] = args.design if args.design == "auto" else args.design.upper()
    return load_settings(**overrides)


def cmd_generate(args) -> int:
    settings = _settings(args)
    from .pipeline import Pipeline

    setup_logging(None, verbose=args.verbose)
    try:
        result = Pipeline(settings, topic=args.topic, save_history=not args.no_history).run()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("hideyoshi_reels").exception("制作に失敗しました: %s", exc)
        return 1
    print("\n🎉 完成しました！（投稿前に approval.json のチェック項目を確認してください）")
    print(f"  タイトル : {result.title}")
    print(f"  形式     : {result.post_format} / デザイン {result.design}")
    for img in result.images:
        print(f"  画像     : {img}")
    if result.video_path:
        print(f"  動画     : {result.video_path}")
    print(f"  フォルダ : {result.output_dir}")
    return 0


def cmd_preview(args) -> int:
    settings = _settings(args)
    from .pipeline import Pipeline

    setup_logging(None, verbose=args.verbose)
    formats = tuple(args.formats.split(",")) if args.formats else ("reel", "feed")
    try:
        out = Pipeline(settings, topic=args.topic, save_history=False).preview(formats)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("hideyoshi_reels").exception("プレビュー作成に失敗しました: %s", exc)
        return 1
    print(f"\n🖼  A〜Dのプレビューを保存しました: {out}")
    print("  compare_reel.png / compare_feed.png で比較できます")
    return 0


def cmd_check(_args) -> int:
    s = load_settings()
    from .factory.fonts import Fonts

    print("=== 設定チェック ===")
    print(f"モード            : {s.mode}")
    print(f"投稿形式          : {s.post_format}（{'×'.join(map(str, s.size))}px）")
    print(f"デザイン          : {s.design_style}")
    print(f"Trend/原稿 (LLM)  : {s.llm_provider()}  {'(' + s.claude_model + ')' if s.llm_provider() != 'mock' else '← ANTHROPIC_API_KEY 未設定'}")
    print(f"キャラ画像        : {s.resolved_image_provider()}  {'' if s.openai_api_key else '← OPENAI_API_KEY 未設定（仮キャラを使用）'}")
    print(f"note URL          : {s.note_url or '未設定（キャプションにリンク誘導を入れません）'}")
    try:
        fonts = Fonts(s.font_path)
        for role, path in fonts.paths.items():
            print(f"フォント({role:5s})  : {path}{'（代替）' if fonts.fake_bold[role] else ''}")
    except RuntimeError as e:
        print(f"フォント          : ✖ {e}")
    import shutil

    print(f"FFmpeg            : {'OK' if shutil.which('ffmpeg') else '✖ 未インストール（リールの動画化に必要）'}")
    return 0


def cmd_history(_args) -> int:
    s = load_settings()
    h = History(s.history_path)
    if not h.entries:
        print("まだ履歴はありません。")
    for e in h.entries:
        print(f"{e.get('created_at', '')[:16]}  [{e.get('format', '?')}/{e.get('design', '?')}] {e.get('title')}"
              f"  -> {e.get('output_dir')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hideyoshi_reels", description="ちび秀吉の受験Instagram投稿 自動制作")
    sub = parser.add_subparsers(dest="command")

    def common(p):
        p.add_argument("--mock", action="store_true", help="APIを使わずモックで制作（無料）")
        p.add_argument("--topic", help="企画のテーマを指定（例: 英語, 夏休み）")
        p.add_argument("--design", choices=[d for d in DESIGN_STYLES] + ["a", "b", "c", "d"],
                       help="デザイン A/B/C/D（auto=テーマに合わせて自動選択）")
        p.add_argument("-v", "--verbose", action="store_true", help="詳細ログを表示")

    g = sub.add_parser("generate", help="投稿を1つ制作する")
    common(g)
    g.add_argument("--format", choices=POST_FORMATS, help="reel（10秒の静止画リール）/ feed / carousel")
    g.add_argument("--no-history", action="store_true", help="履歴に保存しない")
    g.set_defaults(func=cmd_generate)

    p = sub.add_parser("preview", help="同じテーマで A〜D のデザインを試作して比較")
    common(p)
    p.add_argument("--formats", help="例: reel,feed,carousel（既定: reel,feed）")
    p.set_defaults(func=cmd_preview)

    sub.add_parser("check", help="設定・APIキーの確認").set_defaults(func=cmd_check)
    sub.add_parser("history", help="過去の企画一覧").set_defaults(func=cmd_history)
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
