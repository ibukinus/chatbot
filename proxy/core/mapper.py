import os
import pandas as pd
import logging
from typing import Dict, Optional
import config

logger = logging.getLogger(__name__)


class Mapper:
    users_map: Dict[str, str]
    projects_map: Dict[str, str]

    def __init__(self) -> None:
        self.users_map = {}
        self.projects_map = {}
        self.load_mappings()

    def load_mappings(self) -> None:
        """CSVファイルからユーザーとプロジェクトのマッピングを読み込む"""
        try:
            if os.path.exists(config.USERS_CSV_PATH):
                df_users = pd.read_csv(config.USERS_CSV_PATH)
                # カラム検証
                required_cols = {'openproject_user', 'rocketchat_user'}
                if not required_cols.issubset(df_users.columns):
                    raise ValueError(f"Users CSV missing required columns: {required_cols - set(df_users.columns)}")

                self.users_map = dict(zip(df_users['openproject_user'], df_users['rocketchat_user']))
                logger.info(f"Loaded {len(self.users_map)} user mappings.")
            else:
                logger.warning(f"{config.USERS_CSV_PATH} not found. User mapping will be unavailable.")

            if os.path.exists(config.PROJECTS_CSV_PATH):
                df_projects = pd.read_csv(config.PROJECTS_CSV_PATH)
                # カラム検証
                required_cols = {'project_identifier', 'rc_channel'}
                if not required_cols.issubset(df_projects.columns):
                    raise ValueError(f"Projects CSV missing required columns: {required_cols - set(df_projects.columns)}")

                self.projects_map = dict(zip(df_projects['project_identifier'], df_projects['rc_channel']))
                logger.info(f"Loaded {len(self.projects_map)} project mappings.")
            else:
                logger.warning(f"{config.PROJECTS_CSV_PATH} not found. Project mapping will use default channel.")

        except pd.errors.EmptyDataError:
            logger.error("CSV file is empty")
            raise
        except pd.errors.ParserError as e:
            logger.error(f"CSV parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading CSVs: {e}")
            raise

    def get_rc_user(self, op_user: str) -> Optional[str]:
        """OpenProjectのユーザー名に対応するRocket.Chatのユーザー名を取得する"""
        return self.users_map.get(op_user)

    def get_channel(self, project_identifier: str) -> str:
        """プロジェクト識別子に対応するRocket.Chatのチャンネル名を取得する。未定義時はデフォルト値を返す"""
        return self.projects_map.get(project_identifier, config.DEFAULT_CHANNEL)