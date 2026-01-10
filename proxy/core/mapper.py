import os
import pandas as pd
import logging
import config

logger = logging.getLogger(__name__)

class Mapper:
    def __init__(self):
        self.users_map = {}
        self.projects_map = {}
        self.load_mappings()

    def load_mappings(self):
        """CSVファイルからユーザーとプロジェクトのマッピングを読み込む"""
        try:
            if os.path.exists(config.USERS_CSV_PATH):
                df_users = pd.read_csv(config.USERS_CSV_PATH)
                self.users_map = dict(zip(df_users['openproject_user'], df_users['rocketchat_user']))
                logger.info(f"Loaded {len(self.users_map)} user mappings.")
            else:
                logger.warning(f"{config.USERS_CSV_PATH} not found.")

            if os.path.exists(config.PROJECTS_CSV_PATH):
                df_projects = pd.read_csv(config.PROJECTS_CSV_PATH)
                self.projects_map = dict(zip(df_projects['project_identifier'], df_projects['rc_channel']))
                logger.info(f"Loaded {len(self.projects_map)} project mappings.")
            else:
                logger.warning(f"{config.PROJECTS_CSV_PATH} not found.")
                
        except Exception as e:
            logger.error(f"Error loading CSVs: {e}")

    def get_rc_user(self, op_user):
        """OpenProjectのユーザー名に対応するRocket.Chatのユーザー名を取得する"""
        return self.users_map.get(op_user)

    def get_channel(self, project_identifier):
        """プロジェクト識別子に対応するRocket.Chatのチャンネル名を取得する。未定義時はデフォルト値を返す"""
        return self.projects_map.get(project_identifier, config.DEFAULT_CHANNEL)

# グローバルインスタンス
mapper = Mapper()