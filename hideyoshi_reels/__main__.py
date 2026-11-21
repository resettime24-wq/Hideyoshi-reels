"""コマンドライン入口。

使い方:
  python -m hideyoshi_reels generate            # 1本生成（APIキーがあれば本番、無ければモック）
  python -m hideyoshi_reels generate --mock     # 必ずモック（無料）で生成
  python -m hideyoshi_reels generate --topic 英語
  python -m hideyoshi_reels check               # 設定の確認
  python -m hideyoshi_reels history             # 過去の企画一覧
"""

from __future__ import annotations

import argparse
import sys

from .config import load_settings
from .history import History
from .utils import setup_logging


def cmd_generate(args) -> int:
    overrides = {}
    if args.mock:
        overrides["mode"] = "mock"
    if args.draft:  # 動作確認用の軽量レンダリング
        overrides.update(width=540, height=960, fps=24)
    settings = load_settings(**overrides)
    from .pipeline import Pipeline

    setup_logging(None, verbose=args.verbose)
    try:
        result = Pipeline(settings, topic=args.topic, save_history=not args.no_history,
                          keep_work=args.keep_work).run()
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger("hideyoshi_reels").exception("生成に失敗しました: %s", exc)
        return 1
    print("\n🎉 完成しました！")
    print(f"  タイトル : {result.title}")
    print(f"  長さ     : {result.duration:.1f} 秒")
    print(f"  動画     : {result.video_path}")
    print(f"  フォルダ : {result.output_dir}")
    return 0


def cmd_check(_args) -> int:
    s = load_settings()
    from .utils import find_font

    print("=== 設定チェック ===")
    print(f"モード            : {s.mode}")
    print(f"企画・台本 (LLM)  : {s.llm_provider()}  {'(' + s.claude_model + ')' if s.llm_provider() != 'mock' else '← ANTHROPIC_API_KEY 未設定'}")
    print(f"画像生成          : {s.resolved_image_provider()}  {'' if s.openai_api_key else '← OPENAI_API_KEY 未設定'}")
    print(f"背景              : {s.resolved_background_mode()}")
    print(f"音声              : {s.resolved_tts_provider()}")
    try:
        print(f"フォント          : {find_font(s.font_path)}")
    except RuntimeError as e:
        print(f"フォント          : ✖ {e}")
    import shutil

    print(f"FFmpeg            : {'OK' if shutil.which('ffmpeg') else '✖ 未インストール'}")
    return 0


def cmd_history(_args) -> int:
    s = load_settings()
    h = History(s.history_path)
    if not h.entries:
        print("まだ履歴はありません。")
    for e in h.entries:
        print(f"{e.get('created_at', '')[:16]}  {e.get('title')}  [{e.get('category')}]  -> {e.get('output_dir')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hideyoshi_reels", description="ちび秀吉の受験リール自動生成")
    sub = parser.add_subparsers(dest="command")
    g = sub.add_parser("generate", help="リール動画を1本生成する")
    g.add_argument("--mock", action="store_true", help="APIを使わずモックで生成（無料）")
    g.add_argument("--topic", help="企画のテーマを指定（例: 英語, 夏休み）")
    g.add_argument("--draft", action="store_true", help="低解像度で素早く生成（動作確認用）")
    g.add_argument("--no-history", action="store_true", help="履歴に保存しない")
    g.add_argument("--keep-work", action="store_true", help="中間ファイルを残す")
    g.add_argument("-v", "--verbose", action="store_true", help="詳細ログを表示")
    g.set_defaults(func=cmd_generate)
    sub.add_parser("check", help="設定・APIキーの確認").set_defaults(func=cmd_check)
    sub.add_parser("history", help="過去の企画一覧").set_defaults(func=cmd_history)
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
