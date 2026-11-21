# Hideyoshi Reels 🏯 ちび秀吉の早稲田受験リール自動生成

Instagram「@waseda.jyukengoukaku」向けに、**ちびキャラ化した豊臣秀吉が早稲田受験のコツを話す
縦型リール動画（1080×1920 / MP4 / 20〜35秒）を、コマンド1回で1本まるごと作る**システムです。

```bash
python -m hideyoshi_reels generate
```

APIキーが無くても **モックモード（無料）** でデモ動画が完成します。

---

## 目次
1. [できること（5つの工程）](#1-できること5つの工程)
2. [まずは無料で1本作ってみる（モックモード）](#2-まずは無料で1本作ってみるモックモード)
3. [APIキーを設定して本番品質で作る](#3-apiキーを設定して本番品質で作る)
4. [GitHub Actions で実行する（パソコン不要）](#4-github-actions-で実行するパソコン不要)
5. [出力されるファイル](#5-出力されるファイル)
6. [キャラクターの管理](#6-キャラクターの管理)
7. [事実確認（ファクトチェック）の仕組み](#7-事実確認ファクトチェックの仕組み)
8. [費用の目安](#8-費用の目安)
9. [設定一覧](#9-設定一覧)
10. [フォルダ構成・拡張方法](#10-フォルダ構成拡張方法)
11. [テスト](#11-テスト)
12. [困ったときは](#12-困ったときは)
13. [次のステップ：Instagram 自動投稿の準備](#13-次のステップinstagram-自動投稿の準備)

---

## 1. できること（5つの工程）

| 工程 | 内容 | 本番（APIキーあり） | モック（APIキーなし） |
|---|---|---|---|
| ① 企画生成 | フック・保存したくなる有益性・完走したくなる構成を重視した企画を3案作り、過去と重複しない最良案を採用 | Claude | ネタ帳（`data/mock_topics.yaml`）から未使用のものを選択 |
| ② 台本生成 | 0〜2秒フック → 問題提起 → 解説3点 → 結論・保存/フォロー促進。秀吉口調で、最近使った言い回しは避ける | Claude | テンプレート＋言い回しプール |
| ②' 事実確認 | 入試制度・偏差値などをWeb検索で確認。確認できない記述は断定しない表現に自動修正 | Claude＋Web検索 | `data/verified_facts.yaml`＋ルール検出 |
| ③ 画像生成 | 表情5種（喜ぶ・驚く・怒る・考える・解説する）のちび秀吉＋場面ごとの背景＋見出し | OpenAI 画像API | プログラム描画のオリジナル仮キャラ |
| ④ 音声・動画 | ナレーション、字幕（音声と同期）、効果音、BGM、ズームアニメ、場面切り替えをFFmpegで合成 | OpenAI TTS / VOICEVOX | テスト用の合成音 |
| ⑤ 出力 | 動画・企画・台本・各場面画像・キャプション・ハッシュタグ・制作履歴を保存 | ← | ← |

> 効果音とBGMはプログラムで一から合成しているため、著作権上の心配がありません。
> Instagramへの自動投稿は**今回は行いません**（[13章](#13-次のステップinstagram-自動投稿の準備)参照）。

---

## 2. まずは無料で1本作ってみる（モックモード）

### 2-1. 必要なもの
- **Python 3.10 以上**（[公式サイト](https://www.python.org/downloads/)からインストール）
- **FFmpeg**（動画を作るソフト）
  - Mac: `brew install ffmpeg`（[Homebrew](https://brew.sh/ja/) が必要）
  - Windows: `winget install Gyan.FFmpeg` を実行してからターミナルを開き直す
  - Ubuntu: `sudo apt install ffmpeg fonts-noto-cjk`
- 日本語フォント（Mac・Windowsは標準で入っています。見つからない場合は `assets/fonts/` に `.ttf` を置く）

### 2-2. 手順（ターミナルにコピペ）

```bash
# 1. リポジトリをダウンロード
git clone https://github.com/resettime24-wq/Hideyoshi-reels.git
cd Hideyoshi-reels

# 2. 専用の環境を作る（最初の1回だけ）
python -m venv .venv
source .venv/bin/activate        # Windows は  .venv\Scripts\activate

# 3. 必要なパッケージを入れる（最初の1回だけ）
pip install -r requirements.txt

# 4. 動画を1本作る！
python -m hideyoshi_reels generate --mock
```

1分ほどで `output/日時_企画名/reel.mp4` が完成します 🎉

便利なコマンド:

```bash
python -m hideyoshi_reels check              # どのAPIが使われるか確認
python -m hideyoshi_reels generate --topic 英語   # テーマを指定
python -m hideyoshi_reels generate --draft    # 低画質で素早く試す
python -m hideyoshi_reels history            # 過去の企画一覧
```

---

## 3. APIキーを設定して本番品質で作る

### 3-1. 必要なAPIキーと取得方法

| サービス | 用途 | 必須？ | 取得方法 |
|---|---|---|---|
| **Anthropic (Claude)** | 企画・台本・事実確認・キャプション | 強く推奨 | ① [console.anthropic.com](https://console.anthropic.com/) でアカウント作成 → ② 「Billing」でクレジットを購入（$5〜） → ③ 「API Keys」→「Create Key」→ `sk-ant-...` をコピー |
| **OpenAI** | キャラ・背景画像、ナレーション音声 | 推奨 | ① [platform.openai.com](https://platform.openai.com/) でアカウント作成 → ② 「Billing」でクレジットを購入（$5〜） → ③ [API keys](https://platform.openai.com/api-keys) で「Create new secret key」→ `sk-...` をコピー。※画像モデル gpt-image-1 の利用には、OpenAIの組織認証（Organization verification）が求められる場合があります（Settings → Organization → General） |
| VOICEVOX | ナレーション音声（無料） | 任意 | APIキー不要。GitHub Actionsでは `tts: voicevox` を選ぶだけ。ローカルでは [VOICEVOX](https://voicevox.hiroshiba.jp/) アプリを起動して `VOICEVOX_URL=http://localhost:50021` を設定。**キャプションにクレジット（例: VOICEVOX:青山龍星）が必要**ですが、自動で追記されます。キャラクターごとの利用規約も確認してください |

> どちらか片方だけでもOK。キーが無い工程は自動的にモックで動きます。

### 3-2. パソコンで使う場合（.env ファイル）

```bash
cp .env.example .env     # Windows は copy .env.example .env
```

`.env` をメモ帳などで開き、キーを貼り付けて保存します。

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxx
```

その後 `python -m hideyoshi_reels generate` を実行します。

> ⚠️ `.env` は `.gitignore` 済みなので GitHub には上がりません。APIキーを他人に見せたり、コードに直接書いたりしないでください。

---

## 4. GitHub Actions で実行する（パソコン不要）

### 4-1. APIキーを GitHub Secrets に登録（最初の1回だけ）
1. GitHub のリポジトリページ → **Settings** → 左メニュー **Secrets and variables** → **Actions**
2. **New repository secret** をクリック
3. Name に `ANTHROPIC_API_KEY`、Secret にキーを貼り付けて **Add secret**
4. 同様に `OPENAI_API_KEY` も登録

### 4-2. 動画を作る
1. リポジトリの **Actions** タブを開く
2. 左の一覧から **「リール動画を生成」** を選ぶ
3. 右側の **Run workflow** ボタン → ブランチを選び、必要なら項目を変更して緑の **Run workflow**
   - `mode`: auto（本番）/ mock（無料テスト）
   - `topic`: テーマ（空欄ならおまかせ）
   - `tts`: 音声（voicevox なら無料）
4. 5〜10分ほどで完了（緑のチェック）
5. 実行結果のページ下部 **Artifacts** の `reel-番号` をクリックするとZIPでダウンロードできます

企画履歴（`data/history.json`）と生成したキャラ素材は自動でリポジトリに保存され、次回の重複防止・キャラ統一に使われます。

### 4-3. 週3回の自動実行にする（将来用）
`.github/workflows/generate-reel.yml` の以下3行の `#` を消してコミットするだけです（月・水・金 18:00 JST）。

```yaml
  # schedule:
  #   - cron: "0 9 * * 1,3,5"
```

---

## 5. 出力されるファイル

`output/20261121_180000_企画名/` に以下が保存されます。

| ファイル | 内容 |
|---|---|
| `reel.mp4` | 完成動画（1080×1920 / 30fps / H.264 + AAC） |
| `post.txt` | **そのままコピペで投稿できる** キャプション＋ハッシュタグ |
| `caption.txt` / `hashtags.txt` | キャプション本文 / 投稿用ハッシュタグ（既定5個） |
| `hashtags_extended.txt` | 予備のハッシュタグ候補 |
| `plan.json` | 企画内容（フック・有益ポイント・ターゲットなど） |
| `narration.txt` | ナレーション台本（タイムスタンプ・表情・効果音つき） |
| `script.json` | 台本の全データ（場面ごとの画像指示・字幕・ナレーション・効果音） |
| `timeline.json` | 動画のタイムライン（各場面と字幕の開始・終了秒、効果音のタイミング） |
| `subtitles.srt` | 字幕ファイル（他の編集ソフトでも使える） |
| `images/scene_XX.png` | 各場面の画像 / `images/character/` 使用したキャラ素材 |
| `factcheck.json` / `review_checklist.md` | 事実確認の結果 / **投稿前チェックリスト** |
| `production_log.json` | 制作履歴（各工程の所要時間、使ったAPI、概算費用、警告） |
| `run.log` | 詳細ログ（エラー時の調査用） |

全体の企画履歴は `data/history.json` に蓄積されます。

---

## 6. キャラクターの管理

- デザイン方針は `assets/character/character.yaml` に集約（2.5頭身・金の兜と後光の飾り・赤い陣羽織・軍配など）。全画像生成で共通利用します。
- **素材の優先順位**
  1. `assets/character/expressions/<表情>.png`（登録済み素材。毎回これを使うのでキャラが統一される）
  2. 無ければ画像APIで生成 → 1. に保存して次回以降は使い回し
     - `assets/character/reference/` に参照画像があれば、それを元に表情差分を作成
     - 参照画像も無ければ1枚目を生成して `reference/auto_reference.png` として保存し、残りの表情はそれを参照して作成
  3. APIキーが無ければ、プログラム描画の仮オリジナル素材（`assets/character/mock/`）
- デザインを作り直したいときは `expressions/` 内のPNGを削除して再実行してください。
- 表情は `happy`（喜ぶ）/ `surprised`（驚く）/ `angry`（怒る）/ `thinking`（考える）/ `explaining`（解説する）の5種類です。

---

## 7. 事実確認（ファクトチェック）の仕組み

受験情報の誤りはアカウントの信頼を損なうため、3段階で対策しています。

1. **企画・台本の段階**で「数値や入試制度は断定しない」「確認が必要な主張は列挙する」ようAIに指示
2. **本番モード**では Claude がWeb検索で早稲田大学公式サイトなどの一次資料を確認し、確認できなかった記述を「〜と言われておる」「最新の募集要項で確認じゃ」など**断定しない表現に自動で書き換え**
3. 偏差値・倍率・%・点数などを含む文は**ルールでも自動検出**し、`review_checklist.md` に必ず載せる

人が一次資料で確認した事実は `data/verified_facts.yaml` に登録できます（確認日から1年経つと自動で「要再確認」扱い）。
**投稿前に必ず `review_checklist.md` を確認してください。**

---

## 8. 費用の目安

1本あたり（1ドル=150円換算のおおよその目安。実際の金額は各社の料金ページで確認してください）

| 項目 | 目安 |
|---|---|
| Claude（企画・台本・事実確認・キャプション） | 約 20〜40円 |
| OpenAI 画像（背景6枚・品質medium） | 約 50〜60円 |
| OpenAI 画像（キャラ表情5枚・**初回のみ**） | 約 50円 |
| OpenAI 音声（約30秒） | 約 1円 |
| VOICEVOX / GitHub Actions（公開リポジトリ・または無料枠内） | 0円 |
| **合計** | **約 70〜100円／本**（週3本で月 約1,000円前後） |

節約したい場合: `BACKGROUND_MODE=procedural`（背景をプログラム描画）、`IMAGE_QUALITY=low`、`TTS_PROVIDER=voicevox`。
実際にかかった概算は毎回 `production_log.json` の `estimated_cost_jpy` に記録されます。

---

## 9. 設定一覧

すべて `.env`（または GitHub Secrets / 環境変数）で設定します。詳しくは [.env.example](.env.example)。

| 変数 | 既定値 | 説明 |
|---|---|---|
| `HR_MODE` | auto | `mock` で全工程を無料モックに |
| `HR_STRICT` | false | true でAPIエラー時にモックへ切り替えず停止 |
| `CLAUDE_MODEL` / `CLAUDE_EFFORT` | claude-opus-5-5 / medium | 使用モデルと思考の深さ |
| `FACTCHECK_WEB_SEARCH` | true | Web検索による事実確認 |
| `IMAGE_QUALITY` | medium | 画像品質（low/medium/high） |
| `BACKGROUND_MODE` | auto | ai / procedural |
| `TTS_PROVIDER` | auto | openai / voicevox / mock |
| `OPENAI_TTS_VOICE` | onyx | OpenAIの声の種類 |
| `MIN_SECONDS` / `MAX_SECONDS` | 20 / 35 | 動画の長さの範囲（長い台本は話速を上げて収める） |
| `HASHTAG_LIMIT` | 5 | 投稿用ハッシュタグ数 |
| `BGM_ENABLED` | true | BGMのオン/オフ |

チャンネルの方針や台本ルールを変えたいときは `hideyoshi_reels/stages/prompts.py` を編集します。

---

## 10. フォルダ構成・拡張方法

```
hideyoshi_reels/
  __main__.py          コマンド（generate / check / history）
  pipeline.py          5工程をつなぐ本体
  config.py            設定の読み込み
  models.py            データ構造（企画・台本・タイムライン）
  history.py           履歴・重複防止
  llm/claude.py        Claude API
  stages/              ① 企画 ② 台本 ファクトチェック ⑤ キャプション / prompts.py
  images/              ③ 画像（providers.py=画像API, character.py=キャラ管理, compose.py=合成, mock_art.py=仮素材）
  audio/               ④ 音声（tts.py=音声API, sfx.py=効果音・BGM）
  video/               ④ 動画（subtitles.py=字幕, renderer.py=FFmpeg）
  publishers/          将来の自動投稿・インサイト分析のひな形
assets/character/      キャラ設定・参照画像・表情素材
data/                  履歴・モック用ネタ帳・確認済み事実
tests/                 自動テスト
.github/workflows/     GitHub Actions（動画生成・テスト）
```

- 別の画像APIを使う → `images/providers.py` に `ImageProvider` を継承したクラスを追加
- 別の音声API（ElevenLabs など）を使う → `audio/tts.py` に `TTSProvider` を継承したクラスを追加
- 自動投稿・分析 → `publishers/` のインターフェースを実装

---

## 11. テスト

```bash
python -m pytest
```

APIキー不要・無料で、モックでの動画生成に加え、**本番API用のコードも偽のAPIサーバーを相手に**最後まで動くことを確認します。
GitHub に push すると「テスト」ワークフローが自動で実行されます。

---

## 12. 困ったときは

| 症状 | 対処 |
|---|---|
| `ffmpeg が見つかりません` | 2-1 の手順で FFmpeg をインストールし、ターミナルを開き直す |
| `日本語フォントが見つかりません` | `assets/fonts/` に日本語フォント（例: Noto Sans JP）の `.ttf` を置く |
| 字幕が□（豆腐）になる | 同上。`FONT_PATH` でフォントを直接指定することもできます |
| `AuthenticationError` / 401 | APIキーの貼り間違い。前後の空白や改行が入っていないか確認 |
| 画像生成で 403 / organization must be verified | OpenAI の組織認証を完了する（3-1参照）。完了まではモック画像で動きます |
| 本番のはずがモックになった | `python -m hideyoshi_reels check` で確認。`production_log.json` の `fallbacks` に理由が記録されます |
| 同じ企画ばかり（モック時） | モックのネタ帳は8本です。使い切ると再利用します。本番モードでは毎回新規企画になります |

エラーの詳細は各出力フォルダの `run.log` に記録されます（失敗時は `output/_running_*/run.log`）。

---

## 13. 次のステップ：Instagram 自動投稿の準備

今回は自動投稿していません。将来追加するときの準備は次のとおりです。

1. **Instagram をプロアカウントに切り替え**（設定 → アカウントの種類とツール → プロアカウントに切り替える → クリエイター or ビジネス）
2. **Facebookページを作成してInstagramと連携**（Instagram Graph API の利用に必要な場合があります）
3. **[Meta for Developers](https://developers.facebook.com/) でアプリを作成**し、Instagram の API（Content Publishing）を追加
4. 権限 `instagram_content_publish`（ほか基本権限）を付与して**長期アクセストークン**を取得
5. トークンとInstagramユーザーIDを GitHub Secrets に `IG_ACCESS_TOKEN` / `IG_USER_ID` として登録
6. **動画を公開URLで置く場所**を用意（APIは動画ファイルではなくURLを受け取るため。例: Cloudflare R2、AWS S3）
7. `hideyoshi_reels/publishers/instagram.py` の `InstagramPublisher.publish()` を実装（手順はファイル内コメントに記載）

インサイト分析（再生数・保存数）も `publishers/base.py` の `InsightsClient` に実装すれば、
企画生成のプロンプトに「伸びた企画の傾向」をフィードバックする拡張ができます。

---

## 素材・著作権について
- キャラクター: 史実の人物をモチーフにした**オリジナルデザイン**（既存のアニメ・ゲームのキャラに似せないよう指示）
- 仮キャラ・背景・効果音・BGM: すべてプログラムで生成した自作素材
- AI生成画像・音声は各サービスの利用規約に従って利用してください（VOICEVOXはクレジット表記が必要）
