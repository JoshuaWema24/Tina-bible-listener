#!/usr/bin/env python3
"""
app.py — Tina Bible Listener for EasyWorship
GUI entry point.  Run: python app.py
"""
import sys
import os

# ── Ensure the project root is on sys.path so all imports resolve ────────────
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QIcon, QFont

from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Tina Bible Listener")
    app.setOrganizationName("TinaBibleListener")
    app.setApplicationVersion("1.0.0")

    # Default font
    font = QFont("Segoe UI", 12)
    app.setFont(font)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
