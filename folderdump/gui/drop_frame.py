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
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        """ドラッグがフレームに入った瞬間に受理判定を行う。
        ここで accept しないと dropEvent は呼ばれません。
        """
        if e.mimeData().hasUrls():
            # 少なくとも1つがフォルダなら受理
            for u in e.mimeData().urls():
                # QFileInfo を使うと Qt 内で判定できて軽量
                if QtCore.QFileInfo(u.toLocalFile()).isDir():
                    e.acceptProposedAction()
                    return
        e.ignore()
   

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if QtCore.QFileInfo(u.toLocalFile()).isDir():
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
            e.acceptProposedAction()
        else:
            e.ignore()
