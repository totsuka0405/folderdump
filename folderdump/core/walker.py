# folderdump/core/walker.py
"""
フォルダ走査ロジック
- ディレクトリ走査
- スキップログ
- 統計管理
- 一時停止/キャンセル制御
"""

import os
import time
from pathlib import Path
from typing import List, Tuple, Optional, Iterable

from PySide6 import QtCore

from .utils import win_long
from .filters import should_keep
from .utils import win_long, strip_long_prefix



def walk_sorted(dirpath: Path, dirs_first: bool) -> List[Tuple[os.DirEntry, bool]]:
    """
    scandir を使ってフォルダ内を列挙し、ソートして返す
    """
    entries: List[os.DirEntry] = []
    scandir_path = win_long(dirpath)
    with os.scandir(scandir_path) as it:
        for e in it:
            entries.append(e)

    if dirs_first:
        entries.sort(key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
    else:
        entries.sort(key=lambda e: e.name.lower())

    return [(e, e.is_dir(follow_symlinks=False)) for e in entries]


class SkipLog:
    """スキップされたパスと理由を記録"""

    def __init__(self):
        self.rows: List[Tuple[str, str]] = []

    def add(self, path: str, reason: str):
        self.rows.append((path, reason))

    def to_text(self) -> str:
        return "\n".join(f"{p}\t{r}" for p, r in self.rows)

    def count(self) -> int:
        return len(self.rows)


class Stats:
    """走査統計（件数・深さ・時間）"""

    def __init__(self):
        self.total: int = 0
        self.max_depth_seen: int = 0
        self.start: float = time.time()
        self.end: float = self.start

    def tick(self, depth: int):
        self.total += 1
        self.max_depth_seen = max(self.max_depth_seen, depth)

    def stop(self):
        self.end = time.time()

    @property
    def elapsed(self) -> float:
        return self.end - self.start


class CtlFlags:
    """走査キャンセル／一時停止フラグ（Python実装版）"""

    def __init__(self):
        self._canceled = False
        self._paused = False

    def cancel(self):
        self._canceled = True

    def is_canceled(self) -> bool:
        return self._canceled

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def is_paused(self) -> bool:
        return self._paused



def iter_paths(
    root: Path,
    max_depth: Optional[int],
    follow_symlinks: bool,
    includes: List[str],
    excludes: List[str],
    dirs_first: bool,
    folders_only: bool,
    flags: CtlFlags,
    skiplog: SkipLog,
    stats: Stats,
    progress_cb=None,
    negates: List[str] | None = None,
) -> Iterable[Tuple[Path, bool, int]]:
    """
    ディレクトリツリーを深さ優先で走査するジェネレータ
    - .gitignore 否定(!)対応：negates による保持優先
    - Windows 長パス (\\?\\) を相対化前に剥がして統一
    - シンボリックリンクは follow_symlinks で切替
    """
    # root を通常形式の絶対パスに統一
    root = Path(strip_long_prefix(str(root.resolve())))

    stack: List[Tuple[Path, int]] = [(root, 0)]

    while stack:
        if flags.is_canceled():
            break
        while flags.is_paused():
            QtCore.QThread.msleep(100)

        current, depth = stack.pop()
        if max_depth is not None and depth > max_depth:
            continue

        try:
            # current 直下を列挙（walk_sorted 内で win_long を使用）
            for entry, is_dir in reversed(walk_sorted(current, dirs_first)):
                # DirEntry.path (\\?\...) -> 通常形式にしてから絶対化
                entry_abs = Path(strip_long_prefix(entry.path)).resolve()

                # 相対化（形式が揃っていれば OK）
                try:
                    rel = entry_abs.relative_to(root)
                except ValueError:
                    # サブパスでない（ドライブ跨ぎ・リンクなど）→安全側でスキップ
                    skiplog.add(entry.path, "ValueError: not a subpath")
                    continue

                # フィルタ判定（否定 > 除外 > 包含）
                if not should_keep(rel, is_dir, includes, excludes, negates=negates):
                    continue

                # 出力（フォルダのみ or すべて）
                if (not folders_only) or (folders_only and is_dir):
                    yield (rel, is_dir, depth + 1)
                    stats.tick(depth + 1)
                    if progress_cb and stats.total % 50 == 0:
                        progress_cb(stats.total)

                # ディレクトリならスタックへ
                if is_dir:
                    try:
                        # シンボリックリンク制御
                        if entry.is_symlink() and not follow_symlinks:
                            continue
                        # 深さ制限チェック
                        if max_depth is None or depth + 1 < max_depth:
                            # push 時も通常形式に統一
                            stack.append((Path(strip_long_prefix(entry.path)), depth + 1))
                    except PermissionError:
                        skiplog.add(entry.path, "PermissionError on child append")
                        continue

        except PermissionError:
            skiplog.add(str(current), "PermissionError on scandir")
        except OSError as e:
            skiplog.add(str(current), f"OSError: {e}")

