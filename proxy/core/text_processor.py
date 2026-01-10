import re
from .mapper import mapper

def convert_mentions(text):
    r"""
    OpenProjectのメンションタグをRocket.Chatのメンション形式に置換する。
    形式: <mention ... data-text="@User Name" ...>...</mention>
    出力: @mapped_user または @User Name
    """
    if not text:
        return ""

    def replace_match(match):
        # group(1) は data-text="@..." 内のユーザー名
        op_user = match.group(1)
        rc_user = mapper.get_rc_user(op_user)
        
        if rc_user:
            return f"@{rc_user}"
        else:
            return f"@{op_user}"

    # 正規表現の解説:
    # <mention\s+          : <mention と空白で開始
    # [^>]*                : 他の属性をスキップ
    # data-text="@([^"]+)" : data-text="@..." 内のコンテンツをキャプチャ
    # [^>]*>               : 残りの属性をスキップしてタグを閉じる
    # .*?                  : タグ内のコンテンツ（非強欲マッチ）
    # </mention>           : 閉じタグ
    # (?:&nbsp;|\u00a0)?   : メンション直後のノーブレークスペース（あれば）をマッチに含めて除去
    pattern = r'<mention\s+[^>]*data-text="@([^"]+)"[^>]*>.*?</mention>(?:&nbsp;|\u00a0)?'
    return re.sub(pattern, replace_match, text)