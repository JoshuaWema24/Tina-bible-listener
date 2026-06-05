"""
ui/verse_monitor.py
Floating secondary window — large verse display for a second monitor.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizeGrip, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSlot
from PyQt6.QtGui import QColor, QPalette, QFont, QPainter, QLinearGradient

from ui.styles import MONITOR_STYLESHEET


class VerseMonitorWindow(QWidget):
    """
    Always-on-top floating window showing the last detected verse.
    Designed to be moved to a second / confidence monitor.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Tina — Verse Monitor")
        self.setMinimumSize(500, 280)
        self.resize(700, 360)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setStyleSheet(MONITOR_STYLESHEET)
        self._build_ui()
        self._fade_timer = QTimer(self)
        self._idle_timeout = QTimer(self)
        self._idle_timeout.setSingleShot(True)
        self._idle_timeout.timeout.connect(self._show_idle)
        self._restore_geometry()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        # Top bar — title + controls
        topbar = QHBoxLayout()
        title_lbl = QLabel("TINA  ·  VERSE MONITOR")
        title_lbl.setStyleSheet(
            "color: #2a2a3a; font-size: 10px; font-weight: 700; letter-spacing: 3px;"
        )
        topbar.addWidget(title_lbl)
        topbar.addStretch()

        pin_btn = QPushButton("📌 Always On Top")
        pin_btn.setCheckable(True)
        pin_btn.setChecked(True)
        pin_btn.setFixedHeight(26)
        pin_btn.toggled.connect(self._toggle_on_top)
        topbar.addWidget(pin_btn)

        layout.addLayout(topbar)

        # Gold accent bar
        bar = QFrame()
        bar.setObjectName("monitorBar")
        bar.setFixedHeight(3)
        layout.addWidget(bar)

        # Verse reference (big, gold)
        self._ref_label = QLabel("—")
        self._ref_label.setObjectName("monitorRef")
        self._ref_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ref_label.setWordWrap(True)
        layout.addWidget(self._ref_label)

        # Verse text (smaller)
        self._verse_label = QLabel("")
        self._verse_label.setObjectName("monitorText")
        self._verse_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._verse_label.setWordWrap(True)
        layout.addWidget(self._verse_label, stretch=1)

        # Idle hint
        self._idle_label = QLabel("Waiting for verse detection…")
        self._idle_label.setObjectName("monitorIdle")
        self._idle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._idle_label)

        # Bottom status bar
        status_bar = QHBoxLayout()
        self._status_label = QLabel("● IDLE")
        self._status_label.setStyleSheet(
            "color: #2a2a3a; font-size: 10px; letter-spacing: 1px;"
        )
        status_bar.addWidget(self._status_label)
        status_bar.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(24)
        clear_btn.setFixedWidth(56)
        clear_btn.clicked.connect(self._clear)
        status_bar.addWidget(clear_btn)

        layout.addLayout(status_bar)

        # Initial state
        self._show_idle()

    # ── Public API ─────────────────────────────────────────────────────────

    @pyqtSlot(str, float, bool)
    def show_verse(self, ref_display: str, confidence: float, is_correction: bool) -> None:
        """Display a newly detected verse reference."""
        prefix = "⟳  " if is_correction else ""
        self._ref_label.setText(prefix + ref_display)
        self._verse_label.setText("")   # verse text not yet available; cleared
        self._idle_label.hide()
        self._ref_label.show()

        self._status_label.setText(f"● DETECTED  {confidence:.0%}")
        self._status_label.setStyleSheet(
            "color: #c9a84c; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )

        # Animate in with a colour flash
        self._flash_ref()

        # Start idle timer — clear display after 90 seconds of inactivity
        self._idle_timeout.start(90_000)

    def update_verse_text(self, ref_display: str, verse_text: str) -> None:
        """Add fetched verse body text below the reference."""
        if ref_display in (self._ref_label.text() or ""):
            self._verse_label.setText(verse_text)

    @pyqtSlot(str, str)
    def on_verse_displayed(self, ref_display: str, status: str) -> None:
        """Update status indicator based on EW display result."""
        status_map = {
            "ew_success":       ("● IN EW", "#4caf7d"),
            "overlay_fallback": ("● OVERLAY", "#c9a84c"),
            "failed":           ("✗ FAILED", "#e05555"),
        }
        text, color = status_map.get(status, ("● SHOWN", "#8a8a9a"))
        self._status_label.setText(text)
        self._status_label.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )

    # ── Internal helpers ───────────────────────────────────────────────────

    def _show_idle(self) -> None:
        self._ref_label.hide()
        self._verse_label.hide()
        self._idle_label.show()
        self._status_label.setText("● IDLE")
        self._status_label.setStyleSheet(
            "color: #2a2a3a; font-size: 10px; letter-spacing: 1px;"
        )

    def _clear(self) -> None:
        self._ref_label.setText("—")
        self._verse_label.setText("")
        self._show_idle()
        self._idle_timeout.stop()

    def _toggle_on_top(self, on: bool) -> None:
        flags = self.windowFlags()
        if on:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def _flash_ref(self) -> None:
        """Quick gold flash on the reference label."""
        self._ref_label.setStyleSheet(
            "#monitorRef { color: #ffffff; font-size: 36px; font-weight: 700; }"
        )
        QTimer.singleShot(180, lambda: self._ref_label.setStyleSheet(""))

    def _restore_geometry(self) -> None:
        from PyQt6.QtCore import QSettings
        s = QSettings("TinaBibleListener", "VerseMonitor")
        geo = s.value("geometry")
        if geo:
            self.restoreGeometry(geo)

    def closeEvent(self, event) -> None:
        from PyQt6.QtCore import QSettings
        s = QSettings("TinaBibleListener", "VerseMonitor")
        s.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)
