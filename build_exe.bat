pyinstaller ^
--noconfirm ^
--clean ^
--windowed ^
--name "Audio DeConstruct" ^
--icon "assets\Audio DeCostruct Logo.png" ^
--paths . ^
--add-data "assets;assets" ^
--add-data "qt_ui;qt_ui" ^
--hidden-import PyQt6 ^
--hidden-import sounddevice ^
--hidden-import soundfile ^
--hidden-import numpy ^
qt_ui\main.py
