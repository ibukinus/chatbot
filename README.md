# OpenProject - Rocket.Chat Webhook Proxy

OpenProject と Rocket.Chat を連携させる Webhook プロキシサービスです。OpenProject のワークパッケージコメントを自動的に Rocket.Chat チャンネルに通知します。

## 主な機能

- ✅ **メンション変換**: OpenProject のメンションを Rocket.Chat 形式に自動変換
- 🎯 **動的ルーティング**: プロジェクトごとに異なるチャンネルへ自動振り分け
- 👤 **投稿者名解決**: OpenProject API から実名を取得して表示
- 🔄 **フォールバック配信**: チャンネルが存在しない場合はデフォルトチャンネルに自動配信
- 🔁 **リトライ機構**: 接続失敗時の自動リトライ（最大3回、指数バックオフ）
- 💚 **ヘルスチェック**: Kubernetes/Docker 対応の liveness/readiness probe
- 📊 **構造化ログ**: JSON 形式のログ出力でログ集約システムと連携可能
- 🛡️ **型安全性**: Python 型ヒントによる高品質なコード

## クイックスタート

### 前提条件

- Docker & Docker Compose
- `.env` ファイルの設定（`.env.example` を参照）

### 起動

```bash
# サービスの起動
docker compose up --build

# バックグラウンドで起動
docker compose up -d
```

起動後のアクセス先：
- **OpenProject**: http://localhost:8080
- **Rocket.Chat**: http://localhost:3000
- **Webhook Proxy**: http://localhost:5000

### 初期設定

1. **環境変数の設定** (`.env`)
   ```bash
   # 必須設定
   RC_WEBHOOK_URL=http://rocketchat:3000/hooks/xxx/yyy
   OP_API_KEY=your_api_key_here

   # オプション設定
   LOG_LEVEL=INFO
   LOG_FORMAT=text
   ```

2. **ユーザーマッピングの設定** (`proxy/users.csv`)
   ```csv
   openproject_user,rocketchat_user
   Tanaka Taro,tanaka.rc
   OpenProject Admin,admin.rc
   ```

3. **プロジェクトマッピングの設定** (`proxy/projects.csv`)
   ```csv
   project_identifier,rc_channel
   デモプロジェクト,#dev-alerts
   インフラプロジェクト,#infra-log
   ```

4. **Rocket.Chat Webhook の設定**
   - Incoming Webhook を作成
   - **"Allow Overriding Channel"** を有効化（重要）
   - Webhook URL を `.env` に設定

5. **OpenProject Webhook の設定**
   - 管理 → システム設定 → Webhooks
   - 新しい Webhook を作成
   - URL: `http://webhook-proxy:5000/webhook`
   - イベント: ワークパッケージのコメント

## アーキテクチャ

```
OpenProject → webhook-proxy → OpenProject API → Rocket.Chat
   (Port 8080)    (Port 5000)    (User 解決)     (Port 3000)
```

### システム構成

- **openproject**: プロジェクト管理システム（Webhook 送信元）
- **rocketchat**: チャットプラットフォーム（通知送信先）
- **mongodb**: Rocket.Chat のデータベース
- **webhook-proxy**: Python Flask サービス（変換ロジック）

すべてのサービスは `op-rc-net` Docker ネットワークで通信します。

## 運用

### ヘルスチェック

```bash
# Liveness probe（生存確認）
curl http://localhost:5000/health

# Readiness probe（準備完了確認）
curl http://localhost:5000/ready
```

### ログの確認

```bash
# リアルタイムでログを表示
docker compose logs -f webhook-proxy

# エラーログのみ表示（LOG_LEVEL=ERROR に設定）
docker compose logs webhook-proxy | grep ERROR
```

### サービスの停止

```bash
# グレースフルシャットダウン（30秒のグレースピリオド）
docker compose down
```

## 開発

### 依存関係

```bash
cd proxy

# 本番環境用
pip install -r requirements.txt

# 開発・テスト用
pip install -r requirements-dev.txt
```

### テストの実行

```bash
cd proxy

# 全テストの実行
pytest -v

# カバレッジ付き
pytest --cov --cov-report=html

# 型チェック
mypy .
```

### ディレクトリ構造

```
proxy/
├── main.py                # Flask アプリ（Application Factory パターン）
├── config.py              # 設定管理、ロギング、検証
├── requirements.txt       # 本番環境用依存関係
├── requirements-dev.txt   # 開発・テスト用依存関係
├── mypy.ini               # 型チェック設定
├── pytest.ini             # テスト設定
├── core/                  # コアロジック
│   ├── mapper.py          # CSV マッピング
│   └── text_processor.py  # メンション変換
├── services/              # 外部サービス連携
│   ├── openproject.py     # OpenProject API
│   └── rocketchat.py      # Rocket.Chat Webhook
└── tests/                 # テストコード
```

## トラブルシューティング

### アプリケーションが起動しない

1. 環境変数を確認
   ```bash
   docker compose config
   ```

2. CSV ファイルの存在を確認
   ```bash
   ls -la proxy/*.csv
   ```

3. ログを確認
   ```bash
   docker compose logs webhook-proxy
   ```

### ヘルスチェックが失敗する

```bash
# 詳細情報を取得
curl http://localhost:5000/ready | jq .

# checks.details にエラー詳細が表示されます
```

### メンションが変換されない

- `users.csv` の `openproject_user` カラムが OpenProject の表示名（ログイン ID ではない）と一致しているか確認
- CSV ファイルのエンコーディングが UTF-8 であることを確認

### チャンネルへの投稿が失敗する

- Rocket.Chat の Webhook 設定で "Allow Overriding Channel" が有効か確認
- チャンネル名が `#` で始まっているか確認（`projects.csv`）

## 環境変数リファレンス

| 変数名 | 必須 | デフォルト値 | 説明 |
|--------|------|--------------|------|
| RC_WEBHOOK_URL | ✓ | - | Rocket.Chat Incoming Webhook URL |
| OP_API_KEY | ✓ | - | OpenProject API キー |
| OP_API_URL | | http://openproject:80 | OpenProject API URL |
| OP_API_HOST | | localhost:8080 | OpenProject Host ヘッダー |
| DEFAULT_CHANNEL | | #general | デフォルトチャンネル |
| LOG_LEVEL | | INFO | ログレベル（DEBUG/INFO/WARNING/ERROR） |
| LOG_FORMAT | | text | ログ形式（text/json） |

## セキュリティに関する注意

⚠️ **重要**: `.env` ファイルには機密情報が含まれています。

- `.env` ファイルを git にコミットしないでください
- 本番環境では環境変数または Secrets マネージャーを使用してください
- API キーは定期的にローテーションしてください

## ライセンス

このプロジェクトは社内利用を目的としています。

## サポート

- **仕様書**: `doc/仕様書.md`
- **Claude Code ガイド**: `CLAUDE.md`
- **詳細ドキュメント**: `GEMINI.md`

## 変更履歴

### v2.0.0 (2026-01-13)
- ✨ Application Factory パターンへの移行
- ✨ ヘルスチェックエンドポイント追加
- ✨ リトライ機構の実装
- ✨ 型ヒントの全面的な追加
- ✨ 構造化ログ対応
- ✨ テストカバレッジの拡充
- 🐛 エラーハンドリングの改善
- 📝 ドキュメントの充実

### v1.0.0
- 🎉 初回リリース
- ✨ 基本的な Webhook プロキシ機能
- ✨ メンション変換
- ✨ 動的ルーティング
