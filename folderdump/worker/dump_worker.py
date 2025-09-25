# -*- coding: utf-8 -*-
"""
バックグラウンドワーカー
- QThread 上でフォルダ走査を実行
- 進捗通知（progressed）
- キャンセル対応（CtlFlags）
- 統計・スキップログの返却（Stats / SkipLog）
"""

from pathlib import Path
from typing import List, Optional

from PySide6 import QtCore

from folderdump.core.walker import iter_paths, Stats, SkipLog, CtlFlags
from folderdump.core.filters import read_gitignore
from folderdump.core.renderer import (
    render_plain, render_tree, render_markdown,
    render_json, render_csv, render_dot,
)


class DumpWorker(QtCore.QObject):
    """
    バックグラウンドで走査処理を実行するワーカー。
    メインスレッド側（MainWindow）とは Signal/Slot でやり取りします。
    """

    # 進捗：処理件数（iter_paths 内で一定件数ごとに emit）
    progressed = QtCore.Signal(int)

    # 完了：生成テキスト、要素数、統計、スキップログ
    finished = QtCore.Signal(str, int, Stats, SkipLog)

    # 失敗：エラーメッセージ
    failed = QtCore.Signal(str)

    def __init__(
        self,
        roots: List[str],
        fmt: str,
        depth: Optional[int],
        absolute: bool,
        follow_symlinks: bool,
        dirs_first: bool,
        include_patterns: List[str],
        exclude_patterns: List[str],
        folders_only: bool,
        use_gitignore: bool,
        flags: CtlFlags,
    ) -> None:
        super().__init__()
        self.roots = [Path(r) for r in roots]
        self.fmt = (fmt or "plain").lower()
        self.depth = depth
        self.absolute = absolute
        self.follow_symlinks = follow_symlinks
        self.dirs_first = dirs_first
        self.includes = include_patterns or []
        self.excludes = exclude_patterns or []
        self.folders_only = folders_only
        self.use_gitignore = use_gitignore
        # 呼び出し側で必ずインスタンスを渡してください（None 禁止）
        self.flags = flags

    @QtCore.Slot()
    def run(self):
        """
        走査本体。例外は failed で通知し、正常時は finished を emit。
        キャンセルされた場合も、収集済みの結果ぶんは返します。
        """
        try:
            all_texts: List[str] = []
            total_count = 0
            stats = Stats()
            skiplog = SkipLog()

            for root in self.roots:
                # キャンセルチェック（ルートごと）
                if self.flags.is_canceled():
                    break

                if (not root.exists()) or (not root.is_dir()):
                    self.failed.emit(f"フォルダが見つかりません: {root}")
                    return

                # 除外パターンの合成（.gitignore 簡易対応）
                excludes = list(self.excludes)
                if self.use_gitignore:
                    ex2, neg = read_gitignore(root)   # ★ 変更：タプルで受け取る
                    excludes.extend(ex2)
                else:
                    neg = []

                items = list(
                    iter_paths(
                        root=root,
                        max_depth=self.depth,
                        follow_symlinks=self.follow_symlinks,
                        includes=self.includes,
                        excludes=excludes,
                        dirs_first=self.dirs_first,
                        folders_only=self.folders_only,
                        flags=self.flags,
                        skiplog=skiplog,
                        stats=stats,
                        progress_cb=self.progressed.emit,
                        negates=neg,                  # ★ 追加：否定パターンを渡す
                    )
                )

                # 出力フォーマットに変換
                fmt = self.fmt
                if fmt == "tree":
                    text = render_tree(items)
                elif fmt == "plain":
                    text = render_plain(root, items, absolute=self.absolute)
                elif fmt == "markdown":
                    # tree をコードブロック化
                    text = render_markdown(render_tree(items))
                elif fmt == "json":
                    text = render_json(items)
                elif fmt == "csv":
                    text = render_csv(root, items)
                elif fmt == "dot":
                    text = render_dot(items)
                else:
                    # 未知指定は plain 扱い
                    text = render_plain(root, items, absolute=self.absolute)

                all_texts.append(text)
                total_count += len(items)

                # ルート間でもキャンセルを尊重
                if self.flags.is_canceled():
                    break

            # 統計停止（経過時間確定）
            stats.stop()

            # 結果通知（キャンセル時もここに到達する）
            self.finished.emit("\n\n".join(all_texts), total_count, stats, skiplog)

        except Exception as e:
            # 例外は failed でメイン側へ
            self.failed.emit(str(e))
