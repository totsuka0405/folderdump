# folderdump/core/filters.py
import fnmatch
from pathlib import Path
from typing import List, Tuple

def match_any(name: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)

def match_any_path(rel_path: Path, patterns: List[str]) -> bool:
    """パス全体でもマッチできるように（.gitignore 相性向上）"""
    if not patterns:
        return False
    p_str = rel_path.as_posix()
    name = rel_path.name
    return any(
        fnmatch.fnmatch(p_str, pat) or fnmatch.fnmatch(name, pat)
        for pat in patterns
    )

def read_gitignore(root: Path) -> Tuple[List[str], List[str]]:
    """
    最上位 .gitignore を読み取り、(excludes, negates) を返す簡易実装。
    - コメント/空行は除外
    - 先頭 '/' は削除（ルート相対 → ラフにファイル名/相対パスで扱う）
    - 末尾 '/' は削除
    - '!' は否定（negates）として別出力
    """
    gi = root / ".gitignore"
    if not gi.exists():
        return ([], [])
    excludes: List[str] = []
    negates: List[str] = []
    try:
        for line in gi.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            is_neg = s.startswith("!")
            if is_neg:
                s = s[1:].strip()
            if s.startswith("/"):
                s = s[1:]
            if s.endswith("/"):
                s = s.rstrip("/")
            if not s:
                continue
            (negates if is_neg else excludes).append(s)
    except Exception:
        pass
    return (excludes, negates)

def should_keep(
    rel_path: Path,
    is_dir: bool,
    includes: List[str],
    excludes: List[str],
    negates: List[str] | None = None,
) -> bool:
    """否定 > 除外 > 包含 の順で判定（否定は除外を打ち消す）"""
    negates = negates or []

    # まず否定（保持強制）
    if match_any_path(rel_path, negates):
        return True

    # 除外
    if excludes and match_any_path(rel_path, excludes):
        return False

    # 包含（指定があればそれに合致するものだけ）
    if includes:
        return match_any_path(rel_path, includes)

    return True
