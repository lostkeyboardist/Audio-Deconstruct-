import sys
import traceback
from datetime import datetime


def install_crash_handler():
    def handle_exception(exc_type, exc_value, exc_traceback):
        with open("crash.log", "a", encoding="utf-8") as f:
            f.write("\n\n=== Crash {} ===\n".format(datetime.now()))
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception
