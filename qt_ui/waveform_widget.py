import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


class WaveformWidget(QWidget):
    """Minimal DAW-style waveform display with playhead."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._envelope = np.array([], dtype=np.float32)
        self._sample_rate = None
        self._duration = 0.0
        self._position_seconds = 0.0
        self._resolution = 1000
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(56)

    def set_audio_data(self, np_array, sample_rate):
        arr = np.asarray(np_array, dtype=np.float32)
        if arr.size == 0 or sample_rate is None or sample_rate <= 0:
            self._envelope = np.array([], dtype=np.float32)
            self._sample_rate = None
            self._duration = 0.0
            self._position_seconds = 0.0
            self.update()
            return

        if arr.ndim == 2:
            if arr.shape[1] >= 2:
                arr = arr.mean(axis=1)
            else:
                arr = arr[:, 0]
        elif arr.ndim != 1:
            arr = arr.reshape(-1)

        length = arr.shape[0]
        self._sample_rate = float(sample_rate)
        self._duration = length / self._sample_rate

        points = min(self._resolution, max(1, length))
        edges = np.linspace(0, length, points + 1, dtype=int)
        peaks = np.zeros(points, dtype=np.float32)
        for i in range(points):
            start = edges[i]
            end = edges[i + 1]
            if end <= start:
                continue
            seg = arr[start:end]
            peaks[i] = float(np.max(np.abs(seg)))
        self._envelope = np.clip(peaks, 0.0, 1.0)
        self.update()

    def set_position_seconds(self, seconds):
        self._position_seconds = max(0.0, float(seconds))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        width = rect.width()
        height = rect.height()
        if width <= 1 or height <= 1:
            return

        center_y = height / 2.0

        # Center line
        center_pen = QPen(QColor("#2b2f36"))
        center_pen.setWidth(1)
        painter.setPen(center_pen)
        painter.drawLine(0, int(center_y), width, int(center_y))

        # Waveform envelope
        if self._envelope.size > 0:
            wave_pen = QPen(QColor("#1abc9c"))
            wave_pen.setWidth(1)
            painter.setPen(wave_pen)
            count = self._envelope.size
            for i, amp in enumerate(self._envelope):
                x = int((i / max(1, count - 1)) * (width - 1))
                half_h = amp * (height * 0.45)
                painter.drawLine(x, int(center_y - half_h), x, int(center_y + half_h))

        # Playhead
        playhead_x = 0
        if self._duration > 0:
            ratio = max(0.0, min(1.0, self._position_seconds / self._duration))
            playhead_x = int(ratio * (width - 1))
        playhead_pen = QPen(QColor("white"))
        playhead_pen.setWidth(1)
        painter.setPen(playhead_pen)
        painter.drawLine(playhead_x, 0, playhead_x, height)
