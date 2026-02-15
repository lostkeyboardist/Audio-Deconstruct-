from PyQt6.QtCore import QSettings
from version import APP_NAME


class AppSettings:
    def __init__(self):
        self.settings = QSettings(APP_NAME, APP_NAME)

    def set(self, key, value):
        self.settings.setValue(key, value)

    def get(self, key, default=None):
        return self.settings.value(key, default)
