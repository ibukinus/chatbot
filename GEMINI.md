# OpenProject - Rocket.Chat Webhook Proxy

## プロジェクト概要
本プロジェクトは **OpenProject** と **Rocket.Chat** を連携させるための中間ミドルウェアです。OpenProject からの Webhook イベント（主にワークパッケージのコメント）を傍受し、変換処理を行った上で Rocket.Chat に通知を転送します。

## 主な機能
*   **メンション変換**: OpenProject 独自のメンションタグ (`<mention>`) を Rocket.Chat 形式 (`@user`) に変換します。変換には `users.csv` を使用します。
*   **動的ルーティング**: プロジェクト名に基づいて、通知先の Rocket.Chat チャンネルを動的に切り替えます。設定には `projects.csv` を使用します。
*   **投稿者名の解決**: OpenProject API を使用してコメント投稿者の表示名を取得し、Rocket.Chat の投稿者名 (alias) として反映します。
*   **フォールバック配信**: 指定チャンネルへの投稿が失敗した場合、自動的にデフォルトチャンネルへ再試行します。

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
├── main.py             # Flask アプリケーションのエントリーポイント
├── config.py           # 環境変数・パス設定の管理
├── core/
│   ├── mapper.py       # CSV読み込みとマッピングロジック
│   └── text_processor.py # メンション変換、テキスト加工
├── services/
│   ├── openproject.py  # OpenProject API との通信
│   └── rocketchat.py   # Rocket.Chat Webhook への送信
├── tests/              # ユニットテスト
├── users.csv           # ユーザーマッピング設定
└── projects.csv        # プロジェクト/チャンネルマッピング設定
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
*   **`.env`**: APIキー、Webhook URL、デフォルトチャンネル等を設定します。`.env.example` を参照してください。
*   **`users.csv`**: `openproject_user,rocketchat_user` の形式で定義します。
*   **`projects.csv`**: `project_identifier,rc_channel` の形式で定義します。（※現在、プロジェクト名（Title）でのマッチングに対応しています）

### 3. テストの実行
```bash
python3 proxy/tests/test_core.py
```

## 注意事項
*   Rocket.Chat 側の Webhook 設定で **"Allow Overriding Channel" (投稿先の上書きを許可)** が有効である必要があります。
*   OpenProject からプロキシへの通信において、ホスト名検証をパスするために `OP_API_HOST` の設定が重要です。
