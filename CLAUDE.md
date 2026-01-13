# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code (claude.ai/code) にガイダンスを提供します。

## プロジェクト概要

このシステムは **OpenProject** と **Rocket.Chat** を連携する Webhook プロキシです。OpenProject からの Webhook イベント（ワークパッケージのコメント）を傍受し、変換処理を行った上で Rocket.Chat に通知を転送します。主な機能：
- ユーザーメンション変換（OpenProject → Rocket.Chat 形式）
- プロジェクト名に基づく動的チャンネルルーティング
- OpenProject API による投稿者名の解決
- 配信失敗時のデフォルトチャンネルへのフォールバック

**データフロー:**
`OpenProject (Webhook)` → `webhook-proxy (Port 5000)` → `OpenProject API (User resolution)` → `Rocket.Chat (Incoming Webhook)`

## アーキテクチャ

システムは `compose.yml` で定義された 4 つの Docker サービスで構成されています：

1. **openproject** (Port 8080): Webhook の送信元、プロジェクト管理システム
2. **rocketchat** (Port 3000): 通知の送信先、チャットプラットフォーム
3. **mongodb**: Rocket.Chat のデータベースバックエンド
4. **webhook-proxy** (Port 5000): 変換ロジックを処理する Python Flask サービス

すべてのサービスは `op-rc-net` Docker ブリッジネットワークを介して通信します。

### プロキシサービスの構造

```
proxy/
├── main.py                # Flask アプリ（Application Factory パターン）
├── config.py              # 環境変数、ロギング設定、設定検証
├── requirements.txt       # 本番環境用依存関係
├── requirements-dev.txt   # 開発・テスト用依存関係
├── mypy.ini               # 型チェック設定
├── pytest.ini             # テスト設定
├── Dockerfile             # Docker イメージ定義（ヘルスチェック付き）
├── core/
│   ├── mapper.py          # CSV 読み込みとマッピングロジック
│   └── text_processor.py  # メンション変換とテキスト加工
├── services/
│   ├── openproject.py     # OpenProject API クライアント（リトライ機構、キャッシュ付き）
│   └── rocketchat.py      # Rocket.Chat Webhook 送信（フォールバック機能付き）
├── tests/
│   ├── test_core.py       # コアロジックのユニットテスト
│   ├── test_webhook.py    # Webhook エンドポイントのテスト
│   ├── test_services.py   # サービス層のテスト
│   └── test_config.py     # 設定検証のテスト
├── users.csv              # OpenProject → Rocket.Chat ユーザーマッピング
└── projects.csv           # プロジェクト名 → チャンネルマッピング
```

## 開発コマンド

### 全サービスの起動
```bash
docker compose up --build
```

起動後のアクセス先：
- OpenProject: http://localhost:8080
- Rocket.Chat: http://localhost:3000
- Webhook Proxy: http://localhost:5000

### テストの実行
```bash
cd proxy

# 全テストの実行
pytest -v

# カバレッジ付きで実行
pytest --cov --cov-report=term-missing

# 型チェック
mypy .
```

### ヘルスチェック
```bash
# Liveness probe
curl http://localhost:5000/health

# Readiness probe
curl http://localhost:5000/ready
```

### グレースフルシャットダウンでサービス停止
```bash
docker compose down
```

webhook-proxy は 30 秒のグレースピリオドを持ちます。

## 設定

### 環境変数 (.env)

必須設定（詳細は `.env.example` を参照）：

**OpenProject:**
- `OP_SECRET_KEY_BASE`: アプリケーションシークレットキー（`docker-compose run --rm openproject bundle exec rake secret` で生成）
- `OP_API_URL`: Docker 内部ネットワーク通信用 API エンドポイント（デフォルト: `http://openproject:80`）
- `OP_API_KEY`: OpenProject 設定から発行した API アクセストークン
- `OP_API_HOST`: API リクエスト用 Host ヘッダー値（compose.yml の `OPENPROJECT_HOST__NAME` と一致させる必要あり）

**Rocket.Chat:**
- `RC_WEBHOOK_URL`: Incoming webhook URL（形式: `http://rocketchat:3000/hooks/xxx/yyy`）
- `DEFAULT_CHANNEL`: プロジェクトマッピングが見つからない場合や配信失敗時のフォールバックチャンネル
- `ADMIN_USERNAME`, `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASS`: 初期管理ユーザーの認証情報

**ロギング設定:**
- `LOG_LEVEL`: ログレベル（DEBUG, INFO, WARNING, ERROR）デフォルト: INFO
- `LOG_FORMAT`: ログ形式（text または json）デフォルト: text。本番環境では json を推奨

### マッピングファイル

**users.csv** - ユーザーメンション変換：
```csv
openproject_user,rocketchat_user
Tanaka Taro,tanaka.rc
OpenProject Admin,admin.rc
```

**projects.csv** - プロジェクト名（Title）によるチャンネルルーティング：
```csv
project_identifier,rc_channel
デモプロジェクト,#dev-alerts
インフラプロジェクト,#infra-log
```

注意: 現在のシステムはプロジェクトの **Title**（識別子ではない）でマッチングします。`work_package._links.project.title` から抽出されます。

## 主要な実装詳細

### アーキテクチャパターン

**Application Factory パターン** (main.py:15-142):
- `create_app()` 関数でアプリケーションインスタンスを生成
- 依存性注入により、テスタビリティと保守性を向上
- グローバル状態を排除し、各リクエストで独立したコンテキストを使用

**設定検証** (config.py:45-64):
- 起動時に必須環境変数（`RC_WEBHOOK_URL`, `OP_API_KEY`）の存在を確認
- CSV ファイルの存在チェック
- 検証失敗時は RuntimeError を発生させて起動を中止

### Webhook 処理フロー (main.py:40-99)

1. **アクションフィルタリング**: `work_package_comment:comment` アクションのみ処理
2. **メンション変換**: OpenProject の `<mention>` HTML タグを解析し、`users.csv` を使用して `@username` 形式に変換（依存性注入された mapper を使用）
3. **チャンネル解決**: `projects.csv` を介してプロジェクトタイトルから対象チャンネルを決定、見つからない場合は `DEFAULT_CHANNEL` にフォールバック
4. **投稿者解決**: OpenProject API から実際のユーザー名を取得（メモリ内キャッシュ、リトライ機構付き）
5. **メッセージ構成**: `### [Subject] (#ID)\n\n<converted comment>` 形式にフォーマット
6. **フォールバック配信**: 対象チャンネルに送信、400 エラー時はデフォルトチャンネルで再試行
7. **エラーハンドリング**: ValueError（入力データの問題）と Exception（内部エラー）を分離し、内部エラー詳細を公開しない

### ヘルスチェックエンドポイント

**Liveness Probe** (main.py:101-107):
- `/health` エンドポイント
- アプリケーションプロセスが応答可能かのみ確認
- 常に 200 OK を返す

**Readiness Probe** (main.py:109-140):
- `/ready` エンドポイント
- 設定検証と CSV マッピングの読み込み状態を確認
- 準備完了時は 200 OK、未完了時は 503 Service Unavailable を返す

### メンション変換 (core/text_processor.py:6-37)

OpenProject 形式: `<mention class="mention" data-text="@User Name" ...>...</mention>&nbsp;`

変換ロジック：
- `data-text` 属性からユーザー名を抽出
- mapper インスタンス（引数として渡される）を使用して `users.csv` から変換
- マッピングがない場合は元のユーザー名にフォールバック
- 末尾のノーブレークスペースを削除

### API 通信の考慮事項

**OpenProject API アクセス** (services/openproject.py:11-69):
- HTTP Basic Auth を使用（`('apikey', OP_API_KEY)`）
- **重要**: Docker ネットワークホスト名検証のため、`Host` ヘッダーを `OP_API_HOST` に設定
- **リトライ機構**: requests.Session with Retry 戦略（最大3回、指数バックオフ、ステータスコード 429, 500-504 で自動リトライ）
- API 負荷軽減のためユーザーデータのメモリ内キャッシュを実装
- ユーザー解決リクエストは 5 秒のタイムアウト
- エラー種別の区別: Timeout, ConnectionError, JSONDecodeError を個別にハンドリング

**Rocket.Chat 配信** (services/rocketchat.py:10-47):
- JSON ペイロードの `channel` フィールドで指定チャンネルに送信
- **重要**: Webhook 統合で "Allow Overriding Channel"（投稿先の上書きを許可）を有効にする必要あり
- 自動フォールバックを実装：対象チャンネルへの配信が 400 エラーで失敗した場合、`DEFAULT_CHANNEL` で再試行
- エラー種別の区別: HTTPError, Timeout, ConnectionError を個別にハンドリング

## よくある問題

### Host ヘッダーの不一致
OpenProject API 呼び出しが失敗する場合、`.env` の `OP_API_HOST` が `compose.yml` の `OPENPROJECT_HOST__NAME` と一致しているか確認してください。リクエストは Docker 内部ネットワークから発信されますが、ホスト名検証をパスする必要があるためです。

### チャンネル配信の失敗
Rocket.Chat の Webhook 統合で "Allow Overriding Channel" が有効になっていることを確認してください。これがないと、プロキシは動的に異なるチャンネルにメッセージをルーティングできません。

### メンション変換が機能しない
`users.csv` が OpenProject のメンションタグ（`data-text` 属性）に表示される正確な表示名を使用しているか確認してください。ログイン ID ではありません。
