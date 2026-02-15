"""
Audio Workstation - PyQt6 dark theme and styles.
DAW-style: teal accent, flat, soft corners.
"""

DARK_THEME = """
    QMainWindow, QWidget {
        background-color: #0f1115;
        color: #d0d0d0;
    }
    QTabWidget::pane {
        border: none;
        background-color: #14161b;
    }
    QTabBar {
        qproperty-drawBase: 0;
    }
    QTabBar::tab {
        background-color: #1a1d23;
        padding: 10px 20px;
        margin-right: 6px;
        margin-bottom: 4px;
        border: 1px solid #22252b;
        border-bottom: none;
        border-radius: 8px;
        color: #cfcfcf;
    }
    QTabBar::tab:selected {
        background-color: #1abc9c;
        color: #0f1115;
        border: none;
    }
    QPushButton {
        background-color: #1a1d23;
        border: 1px solid #22252b;
        padding: 8px 18px;
        border-radius: 10px;
        color: #d8d8d8;
    }
    QPushButton:hover {
        background-color: #1abc9c;
        color: #0f1115;
    }
    QPushButton:pressed {
        background-color: #16a085;
    }
    QTableWidget {
        background-color: #16181d;
        border: 1px solid #22252b;
        gridline-color: #22252b;
        border-radius: 10px;
        selection-background-color: rgba(26, 188, 156, 0.25);
        selection-color: white;
    }
    QLabel {
        background: transparent;
        color: #d0d0d0;
    }
    QGroupBox {
        background-color: #14161b;
        border: 1px solid #22252b;
        border-radius: 10px;
        margin-top: 12px;
        padding: 16px;
        padding-top: 24px;
        color: #d0d0d0;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        background: transparent;
        padding: 0 6px;
        color: #1abc9c;
    }
    QComboBox:disabled {
        background-color: #16181d;
        color: #666666;
    }
    QCheckBox {
        color: #d0d0d0;
    }
    QLineEdit {
        background-color: #16181d;
        border: 1px solid #22252b;
        border-radius: 8px;
        padding: 8px;
        color: #d0d0d0;
    }
"""

DROP_ZONE_CONTAINER_STYLE = """
    QFrame {
        background-color: #14161b;
        border: 1px solid #22252b;
        border-radius: 14px;
        padding: 12px;
    }
"""

LOG_BOX_STYLE = """
    background-color: #101318;
    border: 1px solid #22252b;
    border-radius: 8px;
    padding: 8px;
    color: #d0d0d0;
"""
