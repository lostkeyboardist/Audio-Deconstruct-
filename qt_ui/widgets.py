"""
Audio Workstation - PyQt6 custom widgets.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}

AUDIO_FILTER = "Audio (*.mp3 *.wav *.flac *.ogg *.m4a);;All (*.*)"


class DropZoneWidget(QWidget):
    """DAW-style drop zone for audio files. Emits filesSelected(list)."""

    filesSelected = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet(
            "background-color: transparent; "
            "border: 2px dashed #1abc9c; "
            "border-radius: 12px;"
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        main_lbl = QLabel("Drag & Drop Files Here")
        main_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_lbl.setStyleSheet("color: #1abc9c; font-size: 14px; background: transparent;")
        main_lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        main_lbl.setAutoFillBackground(False)
        layout.addWidget(main_lbl)

        sub_lbl = QLabel("or Click to Browse")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        sub_lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        sub_lbl.setAutoFillBackground(False)
        layout.addWidget(sub_lbl)

        self.file_count_label = QLabel("No files selected")
        self.file_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_count_label.setStyleSheet("color: #666; font-size: 11px; background: transparent;")
        self.file_count_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.file_count_label.setAutoFillBackground(False)
        layout.addWidget(self.file_count_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    try:
                        ext = Path(url.toLocalFile()).suffix.lower()
                        if ext in AUDIO_EXTENSIONS:
                            event.acceptProposedAction()
                            return
                    except (OSError, ValueError):
                        pass

    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in AUDIO_EXTENSIONS:
                    files.append(str(p.resolve()))
        if files:
            self.file_count_label.setText(f"{len(files)} file(s) selected")
            self.file_count_label.setStyleSheet("color: #1abc9c; font-size: 11px; background: transparent;")
            self.filesSelected.emit(files)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            AUDIO_FILTER,
        )
        files = list(files) if files else []
        if files:
            self.file_count_label.setText(f"{len(files)} file(s) selected")
            self.file_count_label.setStyleSheet("color: #1abc9c; font-size: 11px; background: transparent;")
        else:
            self.file_count_label.setText("No files selected")
            self.file_count_label.setStyleSheet("color: #666; font-size: 11px; background: transparent;")
        self.filesSelected.emit(files)
        super().mousePressEvent(event)
