#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py - FolderDumpApp エントリポイント
- アイコンを開発時/配布時（PyInstaller）どちらでも確実に適用
- Windows タスクバー用 AppUserModelID を設定
"""

import os
import sys

from PySide6 import QtCore, QtWidgets, QtGui

# アプリ本体の MainWindow をインポート
from folderdump.gui.main_window import MainWindow


def resource_path(*parts: str) -> str:
    """
    実行環境に応じて resources への実パスを返す。
    PyInstaller 実行時は sys._MEIPASS（展開先）を参照。
    """
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, *parts)


def set_windows_app_id(app_id: str = "FolderDumpApp.FolderDump.1") -> None:
    """
    Windows のタスクバーで正しいアイコンを使わせるため AppUserModelID を設定。
    ※ QApplication 生成前に呼ぶ必要があります。
    """
    if sys.platform.startswith("win"):
        try:
            import ctypes  # 遅延インポート
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            # 失敗しても致命ではないため握りつぶす
            pass


def main():
    # --- Windows タスクバー用 AppID（QApplication 生成前に設定） ---
    set_windows_app_id()

    # （任意）HiDPI 対応：Qt6 では既定有効だが明示しても問題なし
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

    # Qt アプリケーション生成
    app = QtWidgets.QApplication(sys.argv)

    # アイコンの絶対パス（開発時/配布時の両対応）
    icon_path = resource_path("resources", "icon.ico")
    icon = QtGui.QIcon(icon_path)
    if not icon.isNull():
        # アプリ全体とウィンドウの両方に設定（環境差対策で二重に適用）
        app.setWindowIcon(icon)
    else:
        # 参照失敗時は無視（exe の埋め込みアイコンが使われる想定）
        pass

    # メインウィンドウ生成
    win = MainWindow()
    # 念のためウィンドウにも直接適用（タスクバー環境依存対策）
    if not icon.isNull():
        win.setWindowIcon(icon)

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
