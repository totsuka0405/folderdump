from PySide6 import QtWidgets

def apply_theme(app: QtWidgets.QApplication):
    try:
        import qdarktheme
        qdarktheme.setup_theme("auto")
    except Exception:
        # Fallback to Fusion style
        app.setStyle(QtWidgets.QStyleFactory.create("Fusion"))  # ✅ QStyleFactoryで作成
        app.setStyleSheet(
            """
            QMainWindow { background: #1f2330; color: #eaeef5; }
            QLabel { color: #eaeef5; }
            QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QListWidget {
                background: #2b3040; color: #eaeef5; border: 1px solid #3a3f52; border-radius: 8px; padding: 6px;
            }
            QPushButton { background: #3b82f6; color: white; border: none; border-radius: 8px; padding: 8px 12px; }
            QPushButton:hover { filter: brightness(1.1); }
            QPushButton:disabled { background: #5a657f; }
            QFrame#Card { background: #242938; border: 1px solid #3a3f52; border-radius: 12px; }
            QFrame#DropFrame { background: #242938; border: 2px dashed #515a77; border-radius: 12px; padding: 18px; }
            QProgressBar { background: #2b3040; border: 1px solid #3a3f52; border-radius: 8px; text-align: center; color: #eaeef5; }
            """
        )
