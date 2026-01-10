import logging
from flask import Flask, request, jsonify
from core.mapper import mapper
from core.text_processor import convert_mentions
from services.openproject import op_service
from services.rocketchat import rc_service

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
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
        
        # 1. メンション変換
        converted_notes = convert_mentions(comment_body)
        
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

    except Exception as e:
        logger.exception("Error processing webhook")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Flaskサーバーの起動
    app.run(host='0.0.0.0', port=5000)
