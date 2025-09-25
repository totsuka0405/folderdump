from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets


class DropFrame(QtWidgets.QFrame):
    dropped = QtCore.Signal(list)  # list[str]

    def __init__(self, text: str = "ここにフォルダをドロップ", parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)  # ← 文字列ではなく親ウィジェットを渡す
        self.setAcceptDrops(True)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setObjectName("DropFrame")

        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("font-size: 14px; opacity: 0.8;")
        layout.addWidget(label)

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if Path(u.toLocalFile()).is_dir():
                    e.acceptProposedAction()
                    return
        e.ignore()


    def dropEvent(self, e: QtGui.QDropEvent):
        paths = []
        for u in e.mimeData().urls():
            p = Path(u.toLocalFile())
            if p.is_dir():
                paths.append(str(p))
        if paths:
            self.dropped.emit(paths)
