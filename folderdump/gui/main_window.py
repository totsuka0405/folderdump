# -*- coding: utf-8 -*-
"""
メインウィンドウ
- フォルダ選択（ドラッグ＆ドロップ + 参照ダイアログ）
- フォルダ一覧の可視化／削除／並べ替え
- オプション設定
- DumpWorker に処理を依頼（進捗・キャンセル対応）
- 結果プレビュー・保存・検索・コピー
- 統計表示（件数・最大深さ・スキップ数・経過時間）
"""

from pathlib import Path
from typing import List

from PySide6 import QtWidgets, QtCore, QtGui

from folderdump.worker.dump_worker import DumpWorker
from folderdump.gui.drop_frame import DropFrame
from folderdump.gui.style import apply_theme
from folderdump.core.walker import CtlFlags, Stats, SkipLog


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Folder Dump Tool")
        self.resize(960, 720)

        # ---- 中央ウィジェット & ルートレイアウト ----
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        # ---- ヘッダー（簡易）----
        head = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("📂 フォルダ構成テキスト化ツール")
        font = title.font()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        head.addWidget(title)
        head.addStretch(1)
        root.addLayout(head)

        # ---- フォルダ追加UI（ドロップ + 参照ボタン） ----
        self.drop_frame = DropFrame("ここにフォルダをドロップ")
        self.drop_frame.dropped.connect(self.add_paths)
        root.addWidget(self.drop_frame)

        folders_row = QtWidgets.QHBoxLayout()
        self.folders_list = QtWidgets.QListWidget()
        self.folders_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.folders_list.setMinimumHeight(120)
        folders_row.addWidget(self.folders_list, 1)

        btn_col = QtWidgets.QVBoxLayout()
        self.btn_add = QtWidgets.QPushButton("＋ 参照…")
        self.btn_remove = QtWidgets.QPushButton("－ 選択削除")
        self.btn_clear = QtWidgets.QPushButton("× すべて削除")
        self.btn_up = QtWidgets.QPushButton("↑ 上へ")
        self.btn_down = QtWidgets.QPushButton("↓ 下へ")
        self.btn_add.clicked.connect(self.browse_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_up.clicked.connect(self.move_up)
        self.btn_down.clicked.connect(self.move_down)
        for b in (self.btn_add, self.btn_remove, self.btn_clear, self.btn_up, self.btn_down):
            btn_col.addWidget(b)
        btn_col.addStretch(1)
        folders_row.addLayout(btn_col)
        root.addLayout(folders_row)

        # ---- オプション ----
        opts = QtWidgets.QGridLayout()
        row = 0
        self.fmt_combo = QtWidgets.QComboBox()
        self.fmt_combo.addItems(["plain", "tree", "json", "csv", "dot"])
        self.depth_spin = QtWidgets.QSpinBox()
        self.depth_spin.setRange(0, 50)
        self.depth_spin.setValue(0)
        self.chk_absolute = QtWidgets.QCheckBox("絶対パス（plain/csv）")
        self.chk_folders = QtWidgets.QCheckBox("フォルダのみ")
        self.chk_gitignore = QtWidgets.QCheckBox(".gitignore を適用")
        opts.addWidget(QtWidgets.QLabel("フォーマット"), row, 0)
        opts.addWidget(self.fmt_combo, row, 1)
        opts.addWidget(QtWidgets.QLabel("最大深さ（0=制限なし）"), row, 2)
        opts.addWidget(self.depth_spin, row, 3)
        row += 1
        opts.addWidget(self.chk_absolute, row, 0, 1, 2)
        opts.addWidget(self.chk_folders, row, 2, 1, 1)
        opts.addWidget(self.chk_gitignore, row, 3, 1, 1)
        row += 1
        self.chk_symlinks = QtWidgets.QCheckBox("シンボリックリンクを辿る")
        opts.addWidget(self.chk_symlinks, row, 0, 1, 2)
        row += 1
        root.addLayout(opts)

        # ---- 実行列 ----
        run_row = QtWidgets.QHBoxLayout()
        self.run_btn = QtWidgets.QPushButton("▶ 実行")
        self.run_btn.clicked.connect(self.run_dump)
        run_row.addWidget(self.run_btn)
        run_row.addStretch(1)
        root.addLayout(run_row)

        # ---- 進捗バー + キャンセル ----
        bar_row = QtWidgets.QHBoxLayout()
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # 不確定長
        self.progress.setVisible(False)
        self.btn_cancel = QtWidgets.QPushButton("⏹ キャンセル")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_run)
        bar_row.addWidget(self.progress, 1)
        bar_row.addWidget(self.btn_cancel)
        root.addLayout(bar_row)

        # ---- プレビュー ----
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        root.addWidget(self.text_edit, 1)

        # ---- 統計表示 ----
        self.stats_label = QtWidgets.QLabel("件数: 0 | 最大深さ: 0 | スキップ: 0 | 時間: 0.00s")
        root.addWidget(self.stats_label)

        # ---- 保存 ----
        self.save_btn = QtWidgets.QPushButton("💾 保存…")
        self.save_btn.clicked.connect(self.save_output)
        self.save_btn.setEnabled(False)
        root.addWidget(self.save_btn, 0, QtCore.Qt.AlignRight)

        # ---- 状態 ----
        self.thread: QtCore.QThread | None = None
        self.worker: DumpWorker | None = None
        self.output_text: str = ""
        self.flags = CtlFlags()  # 参照用に初期化（実行時に作り直し）
        self._last_stats: Stats | None = None
        self._last_skiplog: SkipLog | None = None

        # ---- テーマ & ステータスバー ----
        apply_theme(QtWidgets.QApplication.instance())
        self.statusBar().showMessage("準備完了")

        # ---- メニュー/ツールバー & 検索状態 ----
        self._build_menu_and_toolbar()
        self._last_query = ""

    # ========================
    # フォルダ一覧の操作
    # ========================
    def add_paths(self, paths: List[str]):
        """ドロップ or 参照で追加されたパスを一覧に反映（重複排除）"""
        existing = {self.folders_list.item(i).text() for i in range(self.folders_list.count())}
        added = 0
        for p in paths:
            if not p:
                continue
            q = str(Path(p))
            if Path(q).is_dir() and q not in existing:
                self.folders_list.addItem(q)
                existing.add(q)
                added += 1
        if added:
            self.statusBar().showMessage(f"{added} 個のフォルダを追加しました")

    def browse_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "フォルダを選択")
        if d:
            self.add_paths([d])

    def remove_selected(self):
        rows = sorted([i.row() for i in self.folders_list.selectedIndexes()], reverse=True)
        for r in rows:
            self.folders_list.takeItem(r)
        if rows:
            self.statusBar().showMessage(f"{len(rows)} 件を削除しました")

    def clear_all(self):
        self.folders_list.clear()
        self.statusBar().showMessage("すべて削除しました")

    def move_up(self):
        row = self.folders_list.currentRow()
        if row > 0:
            item = self.folders_list.takeItem(row)
            self.folders_list.insertItem(row - 1, item)
            self.folders_list.setCurrentRow(row - 1)

    def move_down(self):
        row = self.folders_list.currentRow()
        if 0 <= row < self.folders_list.count() - 1:
            item = self.folders_list.takeItem(row)
            self.folders_list.insertItem(row + 1, item)
            self.folders_list.setCurrentRow(row + 1)

    def current_roots(self) -> List[str]:
        return [self.folders_list.item(i).text() for i in range(self.folders_list.count())]

    # ========================
    # 実行・保存
    # ========================
    def run_dump(self):
        roots = self.current_roots()
        if not roots:
            QtWidgets.QMessageBox.warning(self, "入力不足", "フォルダを1つ以上追加してください。")
            return

        # UI ロック
        self.run_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress.setVisible(True)
        self.text_edit.setPlainText("処理中…")
        self.statusBar().showMessage("走査を開始しました")

        # フラグは毎回新規作成（前回のキャンセル状態を引きずらない）
        self.flags = CtlFlags()

        self.thread = QtCore.QThread(self)
        self.worker = DumpWorker(
            roots=roots,
            fmt=self.fmt_combo.currentText(),
            depth=(self.depth_spin.value() or None),
            absolute=self.chk_absolute.isChecked(),
            follow_symlinks=self.chk_symlinks.isChecked(),   # ← チェックボックスの値を反映
            dirs_first=True,
            include_patterns=[],
            exclude_patterns=[],
            folders_only=self.chk_folders.isChecked(),
            use_gitignore=self.chk_gitignore.isChecked(),
            flags=self.flags,
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progressed.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def cancel_run(self):
        self.flags.cancel()
        self.btn_cancel.setEnabled(False)
        self.statusBar().showMessage("キャンセル要求を送信しました…")

    def on_progress(self, count: int):
        # 不確定長プログレスなのでテキストのみ更新
        self.statusBar().showMessage(f"{count:,} 件処理中…")

    def on_finished(self, text: str, count: int, stats: Stats, skiplog: SkipLog):
        # 出力
        self.output_text = text
        self.text_edit.setPlainText(text)

        # 統計
        self._last_stats = stats
        self._last_skiplog = skiplog
        self._update_stats_label()

        # UI 開放
        self.progress.setVisible(False)
        self.btn_cancel.setEnabled(False)
        self.run_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

        self.statusBar().showMessage(f"完了：{count:,} 件")

    def _update_stats_label(self):
        if not self._last_stats:
            return
        s = self._last_stats
        skipped = self._last_skiplog.count() if self._last_skiplog else 0
        self.stats_label.setText(
            f"件数: {s.total:,} | 最大深さ: {s.max_depth_seen} | スキップ: {skipped:,} | 時間: {s.elapsed:.2f}s"
        )

    def on_failed(self, msg: str):
        self.progress.setVisible(False)
        self.btn_cancel.setEnabled(False)
        self.run_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        QtWidgets.QMessageBox.critical(self, "エラー", msg)
        self.statusBar().showMessage("エラーが発生しました")

    def save_output(self):
        if not self.output_text:
            return
        fmt = self.fmt_combo.currentText()
        # 拡張子を自動提案
        filters = {
            "plain": ("Text (*.txt)", "txt"),
            "tree": ("Text (*.txt);;Markdown (*.md)", "txt"),
            "json": ("JSON (*.json)", "json"),
            "csv": ("CSV (*.csv)", "csv"),
            "dot": ("Graphviz DOT (*.dot)", "dot"),
        }
        flt, ext = filters.get(fmt, ("Text (*.txt)", "txt"))
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存", f"structure.{ext}", flt)
        if fn:
            Path(fn).write_text(self.output_text, encoding="utf-8")
            self.statusBar().showMessage(f"保存しました：{fn}")

    # ========================
    # メニュー/ツールバー・検索/コピー
    # ========================
    def _build_menu_and_toolbar(self):
        # ---- Actions ----
        style = self.style()

        # Open（フォルダ参照）
        act_open = QtGui.QAction(style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), "Open Folder…", self)
        act_open.setShortcut(QtGui.QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self.browse_folder)

        # Save（保存）
        act_save = QtGui.QAction(style.standardIcon(QtWidgets.QStyle.SP_DialogSaveButton), "Save As…", self)
        act_save.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self.save_output)

        # Copy All（全文コピー）
        act_copy_all = QtGui.QAction(style.standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView), "Copy All", self)
        act_copy_all.setShortcut(QtGui.QKeySequence("Ctrl+Shift+C"))
        act_copy_all.triggered.connect(self.copy_all)

        # Copy Selection（選択コピー）
        act_copy_sel = QtGui.QAction(style.standardIcon(QtWidgets.QStyle.SP_DialogYesButton), "Copy Selection", self)
        act_copy_sel.setShortcut(QtGui.QKeySequence("Ctrl+C"))
        act_copy_sel.triggered.connect(self.copy_selection)

        # Search / Find
        act_find = QtGui.QAction(style.standardIcon(QtWidgets.QStyle.SP_FileDialogContentsView), "Find…", self)
        act_find.setShortcut(QtGui.QKeySequence("Ctrl+F"))
        act_find.triggered.connect(self.find_text)

        act_find_next = QtGui.QAction("Find Next", self)
        act_find_next.setShortcut(QtGui.QKeySequence("F3"))
        act_find_next.triggered.connect(lambda: self._find_in_preview(self._last_query or "", forward=True))

        act_find_prev = QtGui.QAction("Find Previous", self)
        act_find_prev.setShortcut(QtGui.QKeySequence("Shift+F3"))
        act_find_prev.triggered.connect(lambda: self._find_in_preview(self._last_query or "", forward=False))

        # Exit（終了）
        act_exit = QtGui.QAction("Exit", self)
        act_exit.setShortcut(QtGui.QKeySequence("Alt+F4"))
        act_exit.triggered.connect(self.close)

        # ---- Menu Bar ----
        menubar = self.menuBar()
        menu_file = menubar.addMenu("&File")
        menu_file.addAction(act_open)
        menu_file.addAction(act_save)
        menu_file.addSeparator()
        menu_file.addAction(act_exit)

        menu_edit = menubar.addMenu("&Edit")
        menu_edit.addAction(act_copy_all)
        menu_edit.addAction(act_copy_sel)
        menu_edit.addSeparator()
        menu_edit.addAction(act_find)
        menu_edit.addAction(act_find_next)
        menu_edit.addAction(act_find_prev)

        # ---- Tool Bar ----
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addAction(act_open)
        toolbar.addAction(act_save)
        toolbar.addSeparator()
        toolbar.addAction(act_copy_all)
        toolbar.addAction(act_copy_sel)
        toolbar.addSeparator()
        toolbar.addAction(act_find)

    def copy_all(self):
        """プレビュー全文をクリップボードへ"""
        text = self.text_edit.toPlainText()
        if text:
            QtWidgets.QApplication.clipboard().setText(text)
            self.statusBar().showMessage("全文をコピーしました")

    def copy_selection(self):
        """選択範囲をクリップボードへ"""
        cursor = self.text_edit.textCursor()
        sel = cursor.selectedText()
        if sel:
            QtWidgets.QApplication.clipboard().setText(sel)
            self.statusBar().showMessage("選択範囲をコピーしました")
        else:
            self.statusBar().showMessage("選択範囲がありません")

    def find_text(self):
        """検索ダイアログを開いて検索"""
        q, ok = QtWidgets.QInputDialog.getText(self, "検索", "文字列：", QtWidgets.QLineEdit.Normal, getattr(self, "_last_query", ""))
        if ok and q:
            self._last_query = q
            self._find_in_preview(q, forward=True)

    def _find_in_preview(self, query: str, forward: bool = True):
        """プレビュー内を検索（F3/Shift+F3 対応、折り返し検索）"""
        if not query:
            return
        flags = QtGui.QTextDocument.FindFlag(0)
        if not forward:
            flags |= QtGui.QTextDocument.FindBackward

        # 現在位置から検索
        if self.text_edit.find(query, flags):
            return

        # 見つからなければ折り返し
        cursor = self.text_edit.textCursor()
        if forward:
            cursor.movePosition(QtGui.QTextCursor.Start)
        else:
            cursor.movePosition(QtGui.QTextCursor.End)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.find(query, flags)
