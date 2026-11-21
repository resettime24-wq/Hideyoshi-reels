"""Instagram 自動投稿（未実装のひな形）。

※ 今回の実装では自動投稿は行いません。呼び出すと NotImplementedError になります。

今後の実装メモ（Instagram Graph API / Content Publishing）:
  1. Instagram プロアカウント（ビジネス or クリエイター）と Meta 開発者アプリを用意
  2. 長期アクセストークンと Instagram ユーザーIDを GitHub Secrets に保存
     （IG_ACCESS_TOKEN, IG_USER_ID）
  3. 動画を公開URLで取得できる場所に置く（例: S3 / Cloudflare R2 / GitHub Release）
  4. POST /{ig-user-id}/media
       リール: media_type=REELS, video_url=... / フィード: image_url=...
       カルーセル: 各画像を is_carousel_item=true で作成 → media_type=CAROUSEL, children=...
  5. コンテナの status_code が FINISHED になるまで待つ
  6. POST /{ig-user-id}/media_publish (creation_id=...)
  7. インサイト: GET /{media-id}/insights （再生数・保存数・リーチ等）
"""

from __future__ import annotations

from .base import InsightsClient, PostPackage, Publisher


class InstagramPublisher(Publisher):
    def __init__(self, access_token: str = "", ig_user_id: str = ""):
        self.access_token = access_token
        self.ig_user_id = ig_user_id

    def publish(self, package: PostPackage) -> str:
        package.ensure_approved()
        raise NotImplementedError("Instagram への自動投稿はまだ有効化していません（README の『次のステップ』参照）")


class InstagramInsights(InsightsClient):
    def fetch(self, media_id: str) -> dict:
        raise NotImplementedError("インサイト分析は今後追加予定です")
