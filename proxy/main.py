import os
import re
import logging
import requests
import pandas as pd
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Configuration ---
RC_WEBHOOK_URL = os.environ.get("RC_WEBHOOK_URL")
RC_WEBHOOK_TOKEN = os.environ.get("RC_WEBHOOK_TOKEN") # Might be part of URL or header
DEFAULT_CHANNEL = os.environ.get("DEFAULT_CHANNEL", "#general")
OP_API_URL = os.environ.get("OP_API_URL", "http://openproject:80")
OP_API_KEY = os.environ.get("OP_API_KEY")
OP_API_HOST = os.environ.get("OP_API_HOST", "localhost:8080")

# --- Data Loading ---
def load_mappings():
    users_map = {}
    projects_map = {}
    
    try:
        if os.path.exists('users.csv'):
            df_users = pd.read_csv('users.csv')
            # dict(zip(keys, values)) is efficient
            users_map = dict(zip(df_users['openproject_user'], df_users['rocketchat_user']))
            logger.info(f"Loaded {len(users_map)} user mappings.")
        else:
            logger.warning("users.csv not found.")

        if os.path.exists('projects.csv'):
            df_projects = pd.read_csv('projects.csv')
            projects_map = dict(zip(df_projects['project_identifier'], df_projects['rc_channel']))
            logger.info(f"Loaded {len(projects_map)} project mappings.")
        else:
            logger.warning("projects.csv not found.")
            
    except Exception as e:
        logger.error(f"Error loading CSVs: {e}")
        
    return users_map, projects_map

# Load mappings at startup
USERS_MAP, PROJECTS_MAP = load_mappings()

# --- User Cache ---
USER_CACHE = {}

def get_user_name(user_href):
    """
    Fetches the user's name from OpenProject API given their href (e.g., /api/v3/users/4).
    Uses caching to minimize API calls.
    """
    if not user_href:
        return "OpenProject"

    # Check cache first
    if user_href in USER_CACHE:
        return USER_CACHE[user_href]

    # If no API key, cannot fetch
    if not OP_API_KEY:
        return "OpenProject"

    try:
        # user_href is relative, e.g., /api/v3/users/4
        # OP_API_URL should be base, e.g., http://openproject:80
        # Ensure correct URL construction
        url = f"{OP_API_URL.rstrip('/')}{user_href}"
        
        logger.info(f"Fetching user info from {url}")
        headers = {'Host': OP_API_HOST}
        response = requests.get(url, auth=('apikey', OP_API_KEY), headers=headers, timeout=5)
        
        if response.status_code == 200:
            user_data = response.json()
            name = user_data.get('name')
            if name:
                USER_CACHE[user_href] = name
                return name
        else:
            logger.warning(f"Failed to fetch user {user_href}: {response.status_code} - {response.text}")

    except Exception as e:
        logger.error(f"Error fetching user info: {e}")

    return "OpenProject"

# --- Logic ---

def convert_mentions(text):
    r"""
    Replaces OpenProject mention tags with Rocket.Chat mentions.
    Format: <mention ... data-text="@User Name" ...>...</mention>
    Target: @mapped_user or @User Name
    """
    if not text:
        return ""

    def replace_match(match):
        # group(1) is the username inside data-text="@..."
        op_user = match.group(1)
        rc_user = USERS_MAP.get(op_user)
        
        if rc_user:
            return f"@{rc_user}"
        else:
            return f"@{op_user}"

    # Regex explanation:
    # <mention\s+          : Start with <mention and whitespace
    # [^>]*                : Skip other attributes
    # data-text="@([^"]+)" : Capture content inside data-text="@..."
    # [^>]*>               : Skip remaining attributes and close tag
    # .*?                  : Content inside tag (non-greedy)
    # </mention>           : Closing tag
    pattern = r'<mention\s+[^>]*data-text="@([^"]+)"[^>]*>.*?</mention>'
    return re.sub(pattern, replace_match, text)

def determine_channel(project_identifier):
    """
    Determines the target channel based on project identifier.
    """
    return PROJECTS_MAP.get(project_identifier, DEFAULT_CHANNEL)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "ignored", "reason": "no json"}), 400

        # Filter: Check action type
        action = data.get('action')
        if action != 'work_package_comment:comment':
             return jsonify({"status": "ignored", "reason": f"unsupported action: {action}"}), 200

        # Extract Activity and Work Package
        activity = data.get('activity', {})
        embedded = activity.get('_embedded', {})
        work_package = embedded.get('workPackage', {})
        
        # Extract Comment
        comment_body = activity.get('comment', {}).get('raw')
        if not comment_body:
             return jsonify({"status": "ignored", "reason": "no comment content"}), 200

        # Process
        wp_id = work_package.get('id', '?')
        logger.info(f"Processing webhook for WP #{wp_id}")
        
        # 1. Mention Conversion
        converted_notes = convert_mentions(comment_body)
        
        # 2. Routing
        # Note: Payload uses 'title' for project name in _links. 
        # Identifier is not directly available in this payload format without extra API calls.
        # We will use Project Title as the key for mapping.
        project_title = work_package.get('_links', {}).get('project', {}).get('title')
        target_channel = determine_channel(project_title)
        
        # 3. Get Author Name
        user_href = activity.get('_links', {}).get('user', {}).get('href')
        author_name = get_user_name(user_href)

        # 4. Payload Construction
        wp_subject = work_package.get('subject', 'No Subject')
        
        # If RC_WEBHOOK_URL is not set, we can't send
        if not RC_WEBHOOK_URL:
            logger.error("RC_WEBHOOK_URL is not set.")
            return jsonify({"status": "error", "message": "Server misconfiguration"}), 500

        # Note: 'channel' is included now that the integration allows overriding.
        rc_payload = {
            "channel": target_channel,
            "text": f"### [{wp_subject}] (#{wp_id})\n\n{converted_notes}",
            "alias": author_name,
            "icon_emoji": ":clipboard:"
        }

        # 4. Send to Rocket.Chat
        def send_to_rc(payload):
            channel_name = payload.get('channel', 'default')
            logger.info(f"Sending to {channel_name}: {payload.get('text')[:50]}...")
            resp = requests.post(RC_WEBHOOK_URL, json=payload)
            if resp.status_code != 200:
                logger.error(f"Rocket.Chat Error: {resp.status_code} - {resp.text}")
            resp.raise_for_status()
            return resp

        try:
            send_to_rc(rc_payload)
        except requests.exceptions.HTTPError as e:
            # Fallback logic: If 400 Bad Request (likely invalid channel) and not already default
            if e.response.status_code == 400 and target_channel != DEFAULT_CHANNEL:
                logger.warning(f"Failed to post to {target_channel}. Retrying with default channel {DEFAULT_CHANNEL}...")
                rc_payload["channel"] = DEFAULT_CHANNEL
                try:
                    send_to_rc(rc_payload)
                except Exception as retry_e:
                     logger.error(f"Fallback to default channel failed: {retry_e}")
                     raise retry_e 
            else:
                raise e

        return jsonify({"status": "success", "channel": rc_payload.get("channel")}), 200

    except Exception as e:
        logger.exception("Error processing webhook")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
