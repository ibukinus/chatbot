# OpenProject - Rocket.Chat Webhook Proxy

## プロジェクト概要
本プロジェクトは **OpenProject** と **Rocket.Chat** を連携させるための中間ミドルウェアです。OpenProject からの Webhook イベント（主にワークパッケージのコメント）を傍受し、変換処理を行った上で Rocket.Chat に通知を転送します。

## 主な機能
*   **メンション変換**: OpenProject 独自のメンションタグ (`<mention>`) を Rocket.Chat 形式 (`@user`) に変換します。変換には `users.csv` を使用します。
*   **動的ルーティング**: プロジェクト名に基づいて、通知先の Rocket.Chat チャンネルを動的に切り替えます。設定には `projects.csv` を使用します。
*   **投稿者名の解決**: OpenProject API を使用してコメント投稿者の表示名を取得し、Rocket.Chat の投稿者名 (alias) として反映します（キャッシュ機能付き）。
*   **フォールバック配信**: 指定チャンネルへの投稿が失敗した場合、自動的にデフォルトチャンネルへ再試行します。
*   **リトライ機構**: OpenProject API への接続失敗時、自動的にリトライします（最大3回、指数バックオフ）。
*   **ヘルスチェック**: Kubernetes/Docker の liveness/readiness probe に対応した `/health` および `/ready` エンドポイント。
*   **構造化ログ**: JSON 形式のログ出力に対応し、ログ集約システムとの連携が容易です。
*   **型安全性**: Python 型ヒントによるコード品質の向上と IDE サポート。

## アーキテクチャ
システムは以下の Docker サービスで構成されています：

1.  **openproject**: Webhook の送信元（プロジェクト管理）。
2.  **rocketchat**: 通知の送信先（チャットプラットフォーム）。
3.  **mongodb**: Rocket.Chat のデータベースバックエンド。
4.  **webhook-proxy**: ロジックを処理する Python (Flask) サービス。

**データフロー:**
`OpenProject (Webhook)` -> `webhook-proxy (Port 5000)` -> `OpenProject API (User解決)` -> `Rocket.Chat (Incoming Webhook)`

## ディレクトリ構造 (リファクタリング済み)
```text
proxy/
├── main.py                # Flask アプリケーションのエントリーポイント（Application Factory パターン）
├── config.py              # 環境変数・パス設定の管理、ロギング設定、設定検証
├── requirements.txt       # 本番環境用の依存関係
├── requirements-dev.txt   # 開発・テスト用の依存関係
├── mypy.ini               # 型チェック設定
├── pytest.ini             # テスト設定
├── Dockerfile             # Docker イメージ定義（ヘルスチェック付き）
├── core/
│   ├── mapper.py          # CSV読み込みとマッピングロジック
│   └── text_processor.py  # メンション変換、テキスト加工
├── services/
│   ├── openproject.py     # OpenProject API との通信（リトライ機構付き）
│   └── rocketchat.py      # Rocket.Chat Webhook への送信（フォールバック付き）
├── tests/
│   ├── test_core.py       # コアロジックのテスト
│   ├── test_webhook.py    # Webhook エンドポイントのテスト
│   ├── test_services.py   # サービス層のテスト
│   └── test_config.py     # 設定検証のテスト
├── users.csv              # ユーザーマッピング設定
└── projects.csv           # プロジェクト/チャンネルマッピング設定
```

## 開発・運用ガイド

### 1. 起動方法
```bash
docker compose up --build
```
*   **OpenProject**: http://localhost:8080
*   **Rocket.Chat**: http://localhost:3000
*   **Proxy**: http://localhost:5000

### 2. 設定
*   **`.env`**: APIキー、Webhook URL、デフォルトチャンネル、ロギング設定等を設定します。`.env.example` を参照してください。
*   **`users.csv`**: `openproject_user,rocketchat_user` の形式で定義します。
*   **`projects.csv`**: `project_identifier,rc_channel` の形式で定義します。（※現在、プロジェクト名（Title）でのマッチングに対応しています）

#### 環境変数
| 変数名 | 必須 | デフォルト値 | 説明 |
|--------|------|--------------|------|
| RC_WEBHOOK_URL | ✓ | - | Rocket.Chat Incoming Webhook URL |
| OP_API_KEY | ✓ | - | OpenProject API キー |
| OP_API_URL | | http://openproject:80 | OpenProject API URL |
| OP_API_HOST | | localhost:8080 | OpenProject Host ヘッダー |
| DEFAULT_CHANNEL | | #general | デフォルトチャンネル |
| LOG_LEVEL | | INFO | ログレベル（DEBUG, INFO, WARNING, ERROR） |
| LOG_FORMAT | | text | ログ形式（text または json） |

### 3. テストの実行
```bash
# 全テストの実行
cd proxy
pytest -v

# カバレッジ付きで実行
pytest --cov --cov-report=term-missing

# 型チェック
mypy .
```

### 4. ヘルスチェック
```bash
# Liveness probe（生存確認）
curl http://localhost:5000/health

# Readiness probe（準備完了確認）
curl http://localhost:5000/ready
```

Docker のヘルスチェックも自動的に実行されます：
```bash
docker ps
# webhook-proxy が (healthy) と表示されることを確認
```

## 注意事項
*   Rocket.Chat 側の Webhook 設定で **"Allow Overriding Channel" (投稿先の上書きを許可)** が有効である必要があります。
*   OpenProject からプロキシへの通信において、ホスト名検証をパスするために `OP_API_HOST` の設定が重要です。
*   必須環境変数（`RC_WEBHOOK_URL`, `OP_API_KEY`）が設定されていない場合、アプリケーションは起動時にエラーを出力して終了します。
*   CSV ファイル（`users.csv`, `projects.csv`）が存在しない場合、警告ログが出力されますが、アプリケーションは起動します。

## トラブルシューティング

### アプリケーションが起動しない
1. 環境変数が正しく設定されているか確認：`docker compose config`
2. CSV ファイルが存在するか確認：`ls -la proxy/*.csv`
3. ログを確認：`docker compose logs webhook-proxy`

### ヘルスチェックが失敗する
1. `/ready` エンドポイントで詳細を確認：`curl http://localhost:5000/ready`
2. 設定エラーの詳細が `checks.details` に表示されます

### パフォーマンス最適化
*   `LOG_LEVEL=WARNING` に設定して、不要なログ出力を削減
*   `LOG_FORMAT=json` に設定して、ログ集約システムとの連携を効率化
