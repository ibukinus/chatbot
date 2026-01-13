import logging
from typing import Tuple
from flask import Flask, request, jsonify, Response
from config import setup_logging, validate_config
from core.mapper import Mapper
from core.text_processor import convert_mentions
from services.openproject import OpenProjectService
from services.rocketchat import RocketChatService

# ロギング設定（最初に実行）
setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Flask アプリケーションを作成する (Application Factory パターン)

    Returns:
        設定済みの Flask アプリケーション
    """
    app = Flask(__name__)

    # 依存性のインスタンス化
    mapper = Mapper()
    op_service = OpenProjectService()
    rc_service = RocketChatService()

    # 設定検証
    is_valid, errors = validate_config()
    if not is_valid:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        raise RuntimeError("Invalid configuration. Check environment variables and CSV files.")

    logger.info("Application initialized successfully")

    # ルート定義
    @app.route('/webhook', methods=['POST'])
    def webhook() -> Tuple[Response, int]:
        """OpenProjectからのWebhookを受信・処理するエンドポイント"""
        try:
            data = request.json
            if not data:
                return jsonify({"status": "ignored", "reason": "no json"}), 400

            # フィルタリング: ワークパッケージのコメント投稿アクションのみを処理
            action = data.get('action')
            if action != 'work_package_comment:comment':
                return jsonify({"status": "ignored", "reason": f"unsupported action: {action}"}), 200

            # Activity と Work Package 情報を抽出
            activity = data.get('activity', {})
            embedded = activity.get('_embedded', {})
            work_package = embedded.get('workPackage', {})

            # コメント本文を抽出
            comment_body = activity.get('comment', {}).get('raw')
            if not comment_body:
                return jsonify({"status": "ignored", "reason": "no comment content"}), 200

            # 処理開始
            wp_id = work_package.get('id', '?')
            logger.info(f"Processing webhook for WP #{wp_id}")

            # 1. メンション変換（mapper を引数として渡す）
            converted_notes = convert_mentions(comment_body, mapper)

            # 2. 通知先チャンネルの決定 (プロジェクト名に基づく)
            project_title = work_package.get('_links', {}).get('project', {}).get('title')
            target_channel = mapper.get_channel(project_title)

            # 3. 投稿者名の解決 (OpenProject API経由)
            user_href = activity.get('_links', {}).get('user', {}).get('href')
            author_name = op_service.get_user_name(user_href)

            # 4. 通知メッセージの組み立て
            wp_subject = work_package.get('subject', 'No Subject')
            message_text = f"### [{wp_subject}] (#{wp_id})\n\n{converted_notes}"

            # 5. Rocket.Chat への送信
            success, result = rc_service.send_message(target_channel, message_text, alias=author_name)

            if success:
                return jsonify({"status": "success", "channel": result}), 200
            else:
                return jsonify({"status": "error", "message": result}), 500

        except ValueError as e:
            # バリデーションエラー（入力データの問題）
            logger.warning(f"Validation error processing webhook: {e}")
            return jsonify({"status": "error", "message": "Invalid request data"}), 400

        except Exception as e:
            # 予期しないエラー（内部エラー）
            logger.exception("Unexpected error processing webhook")
            # 内部エラー詳細を露出しない
            return jsonify({"status": "error", "message": "Internal server error"}), 500

    @app.route('/health', methods=['GET'])
    def health() -> Tuple[Response, int]:
        """
        Liveness probe: アプリケーションが生きているかチェック
        設定検証は行わず、プロセスが応答可能かのみ確認
        """
        return jsonify({"status": "ok"}), 200

    @app.route('/ready', methods=['GET'])
    def ready() -> Tuple[Response, int]:
        """
        Readiness probe: アプリケーションがリクエストを受け付けられるかチェック
        設定の妥当性と外部依存の状態を確認
        """
        checks = {
            "config": False,
            "csv_files": False,
            "details": []
        }

        # 設定検証
        is_valid, errors = validate_config()
        checks["config"] = is_valid
        if errors:
            checks["details"].extend(errors)

        # CSV マッピング確認
        if mapper.users_map or mapper.projects_map:
            checks["csv_files"] = True
        else:
            checks["details"].append("No CSV mappings loaded")

        # 全体的な準備状態
        is_ready = checks["config"] and checks["csv_files"]

        status_code = 200 if is_ready else 503
        return jsonify({
            "status": "ready" if is_ready else "not ready",
            "checks": checks
        }), status_code

    return app


# アプリケーションインスタンスの作成
app = create_app()


if __name__ == '__main__':
    # 開発サーバー（本番では gunicorn を使用）
    app.run(host='0.0.0.0', port=5000, debug=False)
