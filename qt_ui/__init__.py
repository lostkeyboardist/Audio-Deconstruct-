"""
Audio Workstation - PyQt6 UI package.
"""

from .theme import DARK_THEME, DROP_ZONE_CONTAINER_STYLE, LOG_BOX_STYLE
from .widgets import AUDIO_EXTENSIONS, AUDIO_FILTER, DropZoneWidget

__all__ = [
    "AUDIO_EXTENSIONS",
    "AUDIO_FILTER",
    "DARK_THEME",
    "DROP_ZONE_CONTAINER_STYLE",
    "DropZoneWidget",
    "LOG_BOX_STYLE",
]
