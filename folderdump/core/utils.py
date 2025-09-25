# folderdump/core/utils.py
"""
共通ユーティリティ関数
- Windows 長パス対応
- パターンマッチ補助
"""

import os
import sys
import fnmatch
from pathlib import Path
from typing import List

# OS 判定
IS_WIN = sys.platform.startswith("win")


def win_long(p: str | Path) -> str:
    """Windows 長パス対策。必要に応じて \\?\ プレフィックスを付与。"""
    s = str(p)
    if IS_WIN:
        s = os.path.normpath(s)
        # 既に長パスならそのまま
        if s.startswith("\\\\?\\"):
            return s
        # UNC の場合
        if s.startswith("\\\\"):
            # \\server\share\... -> \\?\UNC\server\share\...
            return "\\\\?\\UNC" + s[1:]
        # 通常ドライブ
        return "\\\\?\\" + s
    return s


def strip_long_prefix(p: str) -> str:
    r"""\\?\ / \\?\UNC の長パスプレフィックスを通常形式へ戻す"""
    if p.startswith("\\\\?\\UNC\\"):
        # \\?\UNC\server\share\path -> \\server\share\path
        return "\\" + p[7:]
    if p.startswith("\\\\?\\"):
        # \\?\C:\path -> C:\path
        return p[4:]
    return p



def match_any(name: str, patterns: List[str]) -> bool:
    """
    名前がいずれかのパターンにマッチするか判定する
    """
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)
