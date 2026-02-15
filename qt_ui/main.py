"""
Audio Workstation - PyQt6 UI with backend queue integration.
"""

import os
import sys
import time
from pathlib import Path

# Allow importing queue_manager and version from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from queue_manager import TaskQueue
from version import APP_NAME, APP_VERSION, APP_AUTHOR, APP_DESCRIPTION
from settings import AppSettings


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSplashScreen,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from qt_ui.theme import DARK_THEME, DROP_ZONE_CONTAINER_STYLE, LOG_BOX_STYLE
from qt_ui.widgets import AUDIO_FILTER, DropZoneWidget
from qt_ui.player_engine import PlayerEngine
from qt_ui.waveform_widget import WaveformWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowIcon(QIcon(resource_path("assets/Audio DeCostruct Logo.png")))
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(DARK_THEME)
        self.app_settings = AppSettings()

        self.selected_files = []
        self.task_queue = TaskQueue()
        self.task_queue.start_processing()
        self.player = PlayerEngine()
        self._was_master_playing = False
        self._track_was_playing = {}

        # Central widget with vertical layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._build_processing_tab(), "Processing")
        tabs.addTab(self._build_playback_tab(), "Playback")
        layout.addWidget(tabs)

        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("About", self._show_about)

        # QTimer: refresh queue table every 500ms
        self._queue_timer = QTimer(self)
        self._queue_timer.timeout.connect(self._refresh_queue_table)
        self._queue_timer.start(500)

        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._update_playback_positions)
        self.playback_timer.start(50)

        QShortcut(QKeySequence("Space"), self, activated=self._on_play_clicked)
        QShortcut(QKeySequence("S"), self, activated=self._on_stop_clicked)
        QShortcut(
            QKeySequence(Qt.Key.Key_Right),
            self,
            activated=lambda: self._seek_master(self._get_master_position() + 5),
        )
        QShortcut(
            QKeySequence(Qt.Key.Key_Left),
            self,
            activated=lambda: self._seek_master(self._get_master_position() - 5),
        )

        geometry = self.app_settings.get("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        self.app_settings.set("window_geometry", self.saveGeometry())
        super().closeEvent(event)

    def _make_label(self, text):
        lbl = QLabel(text)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        lbl.setAutoFillBackground(False)
        return lbl

    def _show_about(self):
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "About",
            f"{APP_NAME}\n\n"
            f"Version: {APP_VERSION}\n\n"
            f"{APP_DESCRIPTION}\n\n"
            f"Author: {APP_AUTHOR}"
        )

    def _build_processing_tab(self):
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Top section: Input (left) + Output (right), matching height and alignment
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # Input: GroupBox header + drop zone container (same style as Output)
        input_gb = QGroupBox("Input")
        input_gb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        input_layout = QVBoxLayout(input_gb)
        input_layout.setSpacing(12)

        drop_container = QFrame()
        drop_container.setStyleSheet(DROP_ZONE_CONTAINER_STYLE)
        drop_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        drop_layout = QVBoxLayout(drop_container)
        drop_layout.setContentsMargins(0, 0, 0, 0)
        self.drop_zone = DropZoneWidget(drop_container)
        self.file_count_label = self.drop_zone.file_count_label
        self.drop_zone.filesSelected.connect(self._on_files_selected)
        drop_layout.addWidget(self.drop_zone)
        input_layout.addWidget(drop_container)

        top_layout.addWidget(input_gb)

        output_gb = QGroupBox("Output")
        output_gb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        output_layout = QVBoxLayout(output_gb)
        output_layout.setSpacing(12)

        output_row = QHBoxLayout()
        output_row.setSpacing(12)
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setPlaceholderText("No folder selected")
        output_row.addWidget(self.output_path_edit)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._on_browse_output)
        output_row.addWidget(browse_btn)

        output_layout.addWidget(self._make_label("Destination Folder"))
        output_layout.addLayout(output_row)
        top_layout.addWidget(output_gb)

        top_layout.setStretch(0, 3)  # Input → 60%
        top_layout.setStretch(1, 2)  # Output → 40%

        layout.addLayout(top_layout)

        # --- Convert GroupBox ---
        convert_gb = QGroupBox("Convert")
        convert_gb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        convert_layout = QFormLayout(convert_gb)
        convert_layout.setSpacing(14)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["WAV", "MP3", "FLAC", "MPEG"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        convert_layout.addRow(self._make_label("Output Format:"), self.format_combo)

        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["128k", "192k", "320k"])
        convert_layout.addRow(self._make_label("Bitrate:"), self.bitrate_combo)

        convert_btn = QPushButton("Convert")
        convert_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        convert_btn.setMinimumHeight(28)
        convert_btn.setStyleSheet("border-radius: 12px;")
        convert_btn.clicked.connect(self._on_convert)
        convert_btn_row = QHBoxLayout()
        convert_btn_row.addStretch()
        convert_btn_row.addWidget(convert_btn)
        convert_btn_row.addStretch()
        convert_layout.addRow(convert_btn_row)

        layout.addWidget(convert_gb, 0)

        # --- Separate GroupBox ---
        separate_gb = QGroupBox("Separate")
        separate_gb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        separate_gb.setMinimumWidth(0)  # Allow shrinking in windowed mode
        separate_layout = QFormLayout(separate_gb)
        separate_layout.setSpacing(14)
        # Keep Separate form behavior stable in windowed mode (no dynamic row wrapping)
        separate_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        separate_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["htdemucs", "htdemucs_ft"])
        separate_layout.addRow(self._make_label("Model:"), self.model_combo)

        self.shifts_combo = QComboBox()
        self.shifts_combo.addItems(["1", "2", "4"])
        separate_layout.addRow(self._make_label("Shifts:"), self.shifts_combo)

        self.overlap_combo = QComboBox()
        self.overlap_combo.addItems(["0.25", "0.5"])
        separate_layout.addRow(self._make_label("Overlap:"), self.overlap_combo)

        # 2x2 grid so stems wrap on narrow windows instead of overflowing
        stems_widget = QWidget()
        stems_widget.setMinimumHeight(48)
        stems_grid = QGridLayout(stems_widget)
        stems_grid.setContentsMargins(0, 0, 0, 0)
        self.chk_vocals = QCheckBox("Vocals")
        self.chk_vocals.setChecked(True)
        self.chk_drums = QCheckBox("Drums")
        self.chk_drums.setChecked(True)
        self.chk_bass = QCheckBox("Bass")
        self.chk_bass.setChecked(True)
        self.chk_other = QCheckBox("Other")
        self.chk_other.setChecked(True)
        stems_grid.addWidget(self.chk_vocals, 0, 0)
        stems_grid.addWidget(self.chk_drums, 0, 1)
        stems_grid.addWidget(self.chk_bass, 1, 0)
        stems_grid.addWidget(self.chk_other, 1, 1)
        separate_layout.addRow(self._make_label("Stems:"), stems_widget)

        separate_btn = QPushButton("Separate")
        separate_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        separate_btn.setMinimumHeight(28)
        separate_btn.setStyleSheet("border-radius: 12px;")
        separate_btn.clicked.connect(self._on_separate)
        separate_btn_row = QHBoxLayout()
        separate_btn_row.addStretch()
        separate_btn_row.addWidget(separate_btn)
        separate_btn_row.addStretch()
        separate_layout.addRow(separate_btn_row)

        layout.addWidget(separate_gb, 0)

        # Log box
        layout.addWidget(self._make_label("Log:"))
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log_box.setStyleSheet(LOG_BOX_STYLE)
        layout.addWidget(self.log_box)
        layout.setStretchFactor(self.log_box, 1)

        self._on_format_changed()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_area.setWidget(content_widget)

        # Queue section: fixed height, visually docked, outside scroll
        queue_container = QFrame()
        queue_container.setStyleSheet(
            "QFrame { border-top: 1px solid #22252b; }"
        )
        queue_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        queue_container_layout = QVBoxLayout(queue_container)
        queue_container_layout.setContentsMargins(0, 8, 0, 0)
        queue_container_layout.setSpacing(4)

        queue_label = self._make_label("Queue")
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels(["ID", "File", "Operation", "Status"])
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.queue_table.verticalHeader().setDefaultSectionSize(28)
        self.queue_table.setRowCount(0)
        row_height = 28
        header_height = self.queue_table.horizontalHeader().height()
        self.queue_table.setMaximumHeight(row_height * 4 + header_height + 8)
        self.queue_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        queue_container_layout.addWidget(queue_label)
        queue_container_layout.addWidget(self.queue_table)

        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area, 1)
        main_layout.addWidget(queue_container, 0)
        return tab

    def _build_playback_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Mode row
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_row.addWidget(self._make_label("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Master Timeline", "Independent Tracks"])
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Top controls row
        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        self.load_audio_btn = QPushButton("Load Audio Files")
        self.load_audio_btn.setStyleSheet("border-radius: 12px;")
        self.load_audio_btn.clicked.connect(self._on_load_playback_files)
        controls_row.addWidget(self.load_audio_btn)

        self.play_btn = QPushButton("Play")
        self.play_btn.setStyleSheet("border-radius: 12px;")
        self.play_btn.clicked.connect(self._on_play_clicked)
        controls_row.addWidget(self.play_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setStyleSheet("border-radius: 12px;")
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        controls_row.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("border-radius: 12px;")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        controls_row.addWidget(self.stop_btn)
        controls_row.addStretch()

        layout.addLayout(controls_row)

        master_timeline_row = QHBoxLayout()
        master_timeline_row.setSpacing(10)
        self.master_timeline = QSlider(Qt.Orientation.Horizontal)
        self.master_timeline.setRange(0, 1000)
        self.master_timeline.setValue(0)
        self.master_timeline.sliderPressed.connect(self._on_master_slider_pressed)
        self.master_timeline.sliderReleased.connect(self._on_master_slider_released_final)
        self.master_timeline.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #22252b; border-radius: 3px; }"
            "QSlider::sub-page:horizontal { background: #1abc9c; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #d0d0d0; width: 14px; margin: -5px 0; border-radius: 7px; }"
        )
        self.master_time_label = QLabel("00:00 / 00:00")
        master_timeline_row.addWidget(self.master_timeline, 1)
        master_timeline_row.addWidget(self.master_time_label)
        layout.addLayout(master_timeline_row)

        # Stem mixer area (scrollable)
        self.mixer_scroll = QScrollArea()
        self.mixer_scroll.setWidgetResizable(True)
        self.mixer_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.mixer_container = QWidget()
        self.mixer_layout = QVBoxLayout(self.mixer_container)
        self.mixer_layout.setContentsMargins(0, 0, 0, 0)
        self.mixer_layout.setSpacing(12)
        self.mixer_layout.addStretch()

        self.mixer_scroll.setWidget(self.mixer_container)
        layout.addWidget(self.mixer_scroll)

        self.playback_volume_sliders = []
        self.playback_mute_buttons = []
        self.track_play_buttons = []
        self.track_pause_buttons = []
        self.track_stop_buttons = []
        self.track_timeline_sliders = []
        self.track_time_labels = []
        self.track_waveforms = []

        # Disabled until audio is loaded.
        self.master_timeline.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.mode_combo.setEnabled(False)

        self._set_playback_mode_ui(True)

        return tab

    def _clear_mixer_rows(self):
        # Remove all row widgets/layouts but keep the trailing stretch.
        while self.mixer_layout.count() > 1:
            item = self.mixer_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                while child_layout.count():
                    child_item = child_layout.takeAt(0)
                    child_widget = child_item.widget()
                    if child_widget is not None:
                        child_widget.deleteLater()
                child_layout.deleteLater()

    def _on_load_playback_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Load Audio Files",
            "",
            AUDIO_FILTER,
        )
        if not file_paths:
            return

        try:
            self.player.load_files(file_paths)
        except Exception as e:
            if hasattr(self, "log_box"):
                self.log_box.appendPlainText(f"Playback load failed: {e}")
            return

        self.master_timeline.setEnabled(True)
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.mode_combo.setEnabled(True)

        self.playback_volume_sliders = []
        self.playback_mute_buttons = []
        self.track_play_buttons = []
        self.track_pause_buttons = []
        self.track_stop_buttons = []
        self.track_timeline_sliders = []
        self.track_time_labels = []
        self.track_waveforms = []
        self._clear_mixer_rows()

        with self.player.lock:
            stems_copy = list(self.player.stems)
            sample_rate = self.player.sample_rate

        for index, path in enumerate(file_paths):
            row_widget = QFrame()
            row_widget.setStyleSheet("QFrame { background-color: #14161b; border: 1px solid #22252b; border-radius: 10px; }")
            row_layout = QVBoxLayout(row_widget)
            row_layout.setContentsMargins(10, 10, 10, 10)
            row_layout.setSpacing(8)

            top_line = QHBoxLayout()
            top_line.setSpacing(8)

            name_label = QLabel(Path(path).stem)
            name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            top_line.addWidget(name_label)

            play_btn = QPushButton("Play")
            play_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            play_btn.setMinimumHeight(28)
            play_btn.setStyleSheet("border-radius: 12px;")
            play_btn.clicked.connect(lambda _checked=False, i=index: self.player.play_track(i))
            top_line.addWidget(play_btn)

            pause_btn = QPushButton("Pause")
            pause_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            pause_btn.setMinimumHeight(28)
            pause_btn.setStyleSheet("border-radius: 12px;")
            pause_btn.clicked.connect(lambda _checked=False, i=index: self.player.pause_track(i))
            top_line.addWidget(pause_btn)

            stop_btn = QPushButton("Stop")
            stop_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            stop_btn.setMinimumHeight(28)
            stop_btn.setStyleSheet("border-radius: 12px;")
            stop_btn.clicked.connect(lambda _checked=False, i=index: self.player.stop_track(i))
            top_line.addWidget(stop_btn)
            top_line.addStretch()
            row_layout.addLayout(top_line)

            waveform = WaveformWidget()
            waveform.setMinimumHeight(70)
            row_layout.addWidget(waveform)
            if index < len(stems_copy) and sample_rate is not None:
                waveform.set_audio_data(stems_copy[index], sample_rate)
            self.track_waveforms.append(waveform)

            timeline_line = QHBoxLayout()
            timeline_line.setSpacing(8)
            track_timeline = QSlider(Qt.Orientation.Horizontal)
            track_timeline.setRange(0, 1000)
            track_timeline.setValue(0)
            track_timeline.sliderPressed.connect(
                lambda i=index: self._on_track_slider_pressed(i)
            )
            track_timeline.sliderReleased.connect(
                lambda i=index, s=track_timeline: self._on_track_slider_released_final(i, s)
            )
            track_timeline.setStyleSheet(
                "QSlider::groove:horizontal { height: 6px; background: #22252b; border-radius: 3px; }"
                "QSlider::sub-page:horizontal { background: #1abc9c; border-radius: 3px; }"
                "QSlider::handle:horizontal { background: #d0d0d0; width: 14px; margin: -5px 0; border-radius: 7px; }"
            )
            track_time_label = QLabel("00:00 / 00:00")
            timeline_line.addWidget(track_timeline, 1)
            timeline_line.addWidget(track_time_label)
            row_layout.addLayout(timeline_line)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(100)
            slider.setStyleSheet(
                "QSlider::groove:horizontal { height: 6px; background: #22252b; border-radius: 3px; }"
                "QSlider::sub-page:horizontal { background: #1abc9c; border-radius: 3px; }"
                "QSlider::handle:horizontal { background: #d0d0d0; width: 14px; margin: -5px 0; border-radius: 7px; }"
            )
            slider.valueChanged.connect(
                lambda value, i=index: self.player.set_volume(i, value / 100.0)
            )
            volume_line = QHBoxLayout()
            volume_line.setSpacing(8)
            volume_line.addWidget(slider, 1)

            mute_btn = QPushButton("Mute")
            mute_btn.setStyleSheet("border-radius: 12px;")
            mute_btn.clicked.connect(
                lambda _checked=False, i=index, btn=mute_btn: self._on_toggle_mute(i, btn)
            )
            volume_line.addWidget(mute_btn)
            row_layout.addLayout(volume_line)

            self.playback_volume_sliders.append(slider)
            self.playback_mute_buttons.append(mute_btn)
            self.track_play_buttons.append(play_btn)
            self.track_pause_buttons.append(pause_btn)
            self.track_stop_buttons.append(stop_btn)
            self.track_timeline_sliders.append(track_timeline)
            self.track_time_labels.append(track_time_label)
            self.mixer_layout.insertWidget(self.mixer_layout.count() - 1, row_widget)
            self.mixer_scroll.ensureWidgetVisible(row_widget)

        self._set_playback_mode_ui(self.mode_combo.currentIndex() == 0)

    def _on_toggle_mute(self, index, button):
        self.player.toggle_mute(index)
        is_muted = False
        with self.player.lock:
            if 0 <= index < len(self.player.muted):
                is_muted = self.player.muted[index]
        button.setText("Unmute" if is_muted else "Mute")

    def _format_time(self, seconds):
        seconds = max(0.0, float(seconds))
        total = int(seconds)
        mins = total // 60
        secs = total % 60
        return f"{mins:02d}:{secs:02d}"

    def _get_master_duration(self):
        return float(self.player.get_duration() or 0.0)

    def _get_track_duration(self, index):
        with self.player.lock:
            if (
                self.player.sample_rate is None
                or not (0 <= index < len(self.player.track_lengths))
                or self.player.track_lengths[index] <= 0
            ):
                return 0.0
            return self.player.track_lengths[index] / float(self.player.sample_rate)

    def _get_master_position(self):
        if hasattr(self.player, "get_master_position"):
            return float(self.player.get_master_position())
        with self.player.lock:
            if not self.player.sample_rate:
                return 0.0
            return self.player.master_position / float(self.player.sample_rate)

    def _get_track_position(self, index):
        if hasattr(self.player, "get_track_position"):
            return float(self.player.get_track_position(index))
        with self.player.lock:
            if not self.player.sample_rate or not (0 <= index < len(self.player.track_positions)):
                return 0.0
            return self.player.track_positions[index] / float(self.player.sample_rate)

    def _seek_master(self, seconds):
        if hasattr(self.player, "seek_master"):
            self.player.seek_master(seconds)
            return
        with self.player.lock:
            if not self.player.stems or not self.player.sample_rate:
                return
            total_len = self.player.stems[0].shape[0]
            frame = int(max(0.0, float(seconds)) * float(self.player.sample_rate))
            frame = max(0, min(frame, total_len))
            self.player.master_position = frame
            if self.player.master_mode:
                for i in range(len(self.player.track_positions)):
                    self.player.track_positions[i] = frame

    def _seek_track(self, index, seconds):
        if hasattr(self.player, "seek_track"):
            self.player.seek_track(index, seconds)
            return
        with self.player.lock:
            if (
                not self.player.stems
                or not self.player.sample_rate
                or not (0 <= index < len(self.player.track_positions))
            ):
                return
            total_len = self.player.stems[0].shape[0]
            frame = int(max(0.0, float(seconds)) * float(self.player.sample_rate))
            frame = max(0, min(frame, total_len))
            self.player.track_positions[index] = frame

    def _on_mode_changed(self, index):
        is_master = index == 0
        self.player.set_master_mode(is_master)
        self._set_playback_mode_ui(is_master)

    def _set_playback_mode_ui(self, is_master):
        controls_enabled = self.mode_combo.isEnabled()
        self.master_timeline.setEnabled(controls_enabled and is_master)
        for btn in self.track_play_buttons:
            btn.setEnabled(controls_enabled and (not is_master))
        for btn in self.track_pause_buttons:
            btn.setEnabled(controls_enabled and (not is_master))
        for btn in self.track_stop_buttons:
            btn.setEnabled(controls_enabled and (not is_master))
        for slider in self.track_timeline_sliders:
            slider.setEnabled(controls_enabled and (not is_master))

    def _on_master_slider_pressed(self):
        self._was_master_playing = False
        if self.player.master_playing:
            self._was_master_playing = True
            self.player.pause_master()

    def _on_master_slider_released_final(self):
        duration = self._get_master_duration()
        if duration <= 0:
            return
        seconds = (self.master_timeline.value() / 1000.0) * duration
        self._seek_master(seconds)
        if getattr(self, "_was_master_playing", False):
            self.player.play_master()
        self._was_master_playing = False

    def _on_track_slider_pressed(self, index):
        self._track_was_playing = {}
        with self.player.lock:
            if 0 <= index < len(self.player.track_playing):
                self._track_was_playing[index] = self.player.track_playing[index]
        self.player.pause_track(index)

    def _on_track_slider_released_final(self, index, slider):
        track_duration = self._get_track_duration(index)
        if track_duration <= 0:
            return
        seconds = (slider.value() / 1000.0) * track_duration
        self._seek_track(index, seconds)
        if getattr(self, "_track_was_playing", {}).get(index, False):
            self.player.play_track(index)
        self._track_was_playing[index] = False

    def _on_play_clicked(self):
        if self.mode_combo.currentIndex() == 0:
            self.player.play_master()
        else:
            self.player.play()

    def _on_pause_clicked(self):
        self.player.pause()

    def _on_stop_clicked(self):
        self.player.stop()

    def _update_playback_positions(self):
        master_duration = self._get_master_duration()
        if master_duration <= 0:
            return

        with self.player.lock:
            is_master_playing = bool(self.player.master_playing)
            track_playing_states = list(self.player.track_playing)

        if is_master_playing:
            self.play_btn.setStyleSheet("border-radius: 12px; background-color: #1abc9c; color: black;")
        else:
            self.play_btn.setStyleSheet("border-radius: 12px;")

        if self.mode_combo.currentIndex() == 0:
            pos = self._get_master_position()
            value = int(max(0.0, min(1.0, pos / master_duration)) * 1000)
            if not self.master_timeline.isSliderDown():
                self.master_timeline.blockSignals(True)
                self.master_timeline.setValue(value)
                self.master_timeline.blockSignals(False)
            self.master_time_label.setText(
                f"{self._format_time(pos)} / {self._format_time(master_duration)}"
            )
            if hasattr(self, "track_waveforms"):
                master_pos = self._get_master_position()
                for wf in self.track_waveforms:
                    wf.set_position_seconds(master_pos)
        else:
            for i, slider in enumerate(self.track_timeline_sliders):
                pos = self._get_track_position(i)
                track_duration = self._get_track_duration(i)
                if track_duration > 0:
                    value = int(max(0.0, min(1.0, pos / track_duration)) * 1000)
                else:
                    value = 0
                if not slider.isSliderDown():
                    slider.blockSignals(True)
                    slider.setValue(value)
                    slider.blockSignals(False)
                if i < len(self.track_time_labels):
                    self.track_time_labels[i].setText(
                        f"{self._format_time(pos)} / {self._format_time(track_duration)}"
                    )
                if hasattr(self, "track_waveforms") and i < len(self.track_waveforms):
                    self.track_waveforms[i].set_position_seconds(pos)
            self.master_time_label.setText(
                f"{self._format_time(self._get_master_position())} / {self._format_time(master_duration)}"
            )

        for i, btn in enumerate(self.track_play_buttons):
            is_playing = i < len(track_playing_states) and track_playing_states[i]
            if self.mode_combo.currentIndex() == 1 and is_playing:
                btn.setStyleSheet("border-radius: 12px; background-color: #1abc9c; color: black;")
            else:
                btn.setStyleSheet("border-radius: 12px;")

    def _on_files_selected(self, files):
        self.selected_files = files or []
        self.log_box.clear()
        for f in self.selected_files:
            self.log_box.appendPlainText(Path(f).name)

    def _on_browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_path_edit.setText(path)

    def _on_format_changed(self):
        fmt = self.format_combo.currentText().upper()
        self.bitrate_combo.setEnabled(fmt in ("MP3", "MPEG"))

    def select_files(self):
        """Legacy: open file dialog (drop zone handles this now)."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            AUDIO_FILTER,
        )
        if files:
            self._on_files_selected(list(files))

    def _on_convert(self):
        if not self.selected_files:
            self.log_box.appendPlainText("No files selected.")
            return
        selected_format = self.format_combo.currentText().lower()
        selected_bitrate = self.bitrate_combo.currentText()
        for f in self.selected_files:
            if selected_format in ("mp3", "mpeg"):
                params = {
                    "output_dir": self.output_path_edit.text(),
                    "output_format": selected_format,
                    "bitrate": selected_bitrate,
                }
            else:
                params = {
                    "output_dir": self.output_path_edit.text(),
                    "output_format": selected_format,
                }
            self.task_queue.add_task(f, "convert", params)
        self.log_box.appendPlainText(f"Added {len(self.selected_files)} convert tasks.")

    def _on_separate(self):
        if not self.selected_files:
            self.log_box.appendPlainText("No files selected.")
            return
        selected_stems = []
        if self.chk_vocals.isChecked():
            selected_stems.append("vocals")
        if self.chk_drums.isChecked():
            selected_stems.append("drums")
        if self.chk_bass.isChecked():
            selected_stems.append("bass")
        if self.chk_other.isChecked():
            selected_stems.append("other")
        if not selected_stems:
            self.log_box.appendPlainText("Please select at least one stem.")
            return
        try:
            selected_model = self.model_combo.currentText()
            selected_shifts = int(self.shifts_combo.currentText())
            selected_overlap = float(self.overlap_combo.currentText())
        except (ValueError, TypeError) as e:
            self.log_box.appendPlainText(f"Invalid shifts or overlap: {e}")
            return
        for f in self.selected_files:
            params = {
                "output_dir": self.output_path_edit.text(),
                "model": selected_model,
                "use_gpu": True,
                "shifts": selected_shifts,
                "overlap": selected_overlap,
                "selected_stems": selected_stems,
            }
            self.task_queue.add_task(f, "stem", params)
        self.log_box.appendPlainText(f"Added {len(self.selected_files)} stem tasks.")

    def _refresh_queue_table(self):
        tasks = self.task_queue.get_tasks()
        self.queue_table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.queue_table.setItem(row, 0, QTableWidgetItem(str(t["id"])))
            self.queue_table.setItem(row, 1, QTableWidgetItem(Path(t["file_path"]).name))
            self.queue_table.setItem(row, 2, QTableWidgetItem(t["operation"]))
            self.queue_table.setItem(row, 3, QTableWidgetItem(t["status"]))


if __name__ == "__main__":
    from crash_handler import install_crash_handler
    install_crash_handler()

    app = QApplication(sys.argv)
    app.setApplicationName("Audio DeConstruct")
    app.setOrganizationName("Audio DeConstruct")
    app.setOrganizationDomain("audiodeconstruct.local")
    app.setWindowIcon(QIcon(resource_path("assets/Audio DeCostruct Logo.png")))

    start_time = time.time()

    pixmap = QPixmap(resource_path("assets/Audio DeCostruct Logo.png"))
    pixmap = pixmap.scaled(
        420,
        420,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    splash.show()
    app.processEvents()
    screen = app.primaryScreen().availableGeometry()
    splash.move(
        screen.x() + (screen.width() - splash.width()) // 2,
        screen.y() + (screen.height() - splash.height()) // 2,
    )

    splash.showMessage(
        "Loading Audio DeConstruct...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        Qt.GlobalColor.white,
    )

    window = MainWindow()

    minimum_splash_time = 3000  # ms

    def finish_startup():
        elapsed = time.time() - start_time
        remaining = max(0, minimum_splash_time / 1000.0 - elapsed)

        def show_main():
            window.setWindowOpacity(0.0)
            window.show()
            splash.finish(window)

            def fade():
                opacity = window.windowOpacity()
                if opacity < 1.0:
                    window.setWindowOpacity(opacity + 0.05)
                else:
                    fade_timer.stop()

            fade_timer = QTimer()
            fade_timer.timeout.connect(fade)
            fade_timer.start(30)

        QTimer.singleShot(int(remaining * 1000), show_main)

    finish_startup()
    sys.exit(app.exec())
