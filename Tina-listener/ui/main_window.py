"""
ui/main_window.py
Main operator window — left sidebar + tabbed content area.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QTabWidget, QSizePolicy, QStatusBar,
    QMessageBox, QSpacerItem
)
from PyQt6.QtCore import (
    Qt, QTimer, QSettings, QSize, pyqtSlot, QPropertyAnimation,
    QEasingCurve, QRect
)
from PyQt6.QtGui import QFont, QColor, QPixmap, QPainter, QPen, QBrush, QIcon

from ui.styles      import DARK_STYLESHEET
from ui.live_feed   import LiveFeedWidget
from ui.verse_history import VerseHistoryWidget
from ui.settings_panel import SettingsPanel
from ui.backend_worker  import BackendWorker, BackendSignals, ResendWorker
from ui.verse_monitor   import VerseMonitorWindow


# ─────────────────────────────────────────────────────────────────────────────
# Pulsing status dot widget
# ─────────────────────────────────────────────────────────────────────────────

class StatusDot(QWidget):
    """A small circular indicator that pulses when active."""

    GREEN = "#4caf7d"
    RED   = "#e05555"
    GREY  = "#3a3a4a"
    GOLD  = "#c9a84c"

    def __init__(self, size: int = 10, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = self.GREY
        self._dot_size = size
        self._pulse_phase = 0.0
        self._active = False
        self.setFixedSize(size + 8, size + 8)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(50)
        self._pulse_timer.timeout.connect(self._tick_pulse)

    def set_state(self, color: str, pulsing: bool = False) -> None:
        self._color = color
        if pulsing and not self._pulse_timer.isActive():
            self._pulse_timer.start()
        elif not pulsing:
            self._pulse_timer.stop()
            self._pulse_phase = 0.0
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() // 2
        cy = self.height() // 2
        r = self._dot_size // 2

        # Glow ring when pulsing
        if self._pulse_timer.isActive():
            glow_r = r + 3 + int(self._pulse_phase * 4)
            glow_color = QColor(self._color)
            glow_color.setAlpha(max(0, 80 - int(self._pulse_phase * 80)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow_color))
            p.drawEllipse(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2)

        # Dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(self._color)))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    def _tick_pulse(self) -> None:
        self._pulse_phase = (self._pulse_phase + 0.07) % 1.0
        self.update()


# ─────────────────────────────────────────────────────────────────────────────
# Status row helper
# ─────────────────────────────────────────────────────────────────────────────

class StatusRow(QWidget):
    """A labelled status dot row for the sidebar."""

    def __init__(self, label_text: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._dot = StatusDot(10)
        self._dot.set_state(StatusDot.GREY)
        layout.addWidget(self._dot)

        lbl = QLabel(label_text)
        lbl.setObjectName("statusLabel")
        layout.addWidget(lbl)
        layout.addStretch()

        self._state_lbl = QLabel("—")
        self._state_lbl.setStyleSheet("color: #3a3a4a; font-size: 11px;")
        layout.addWidget(self._state_lbl)

    def set_ok(self, ok: bool, active_text: str = "OK", inactive_text: str = "—") -> None:
        if ok:
            self._dot.set_state(StatusDot.GREEN, pulsing=True)
            self._state_lbl.setText(active_text)
            self._state_lbl.setStyleSheet("color: #4caf7d; font-size: 11px;")
        else:
            self._dot.set_state(StatusDot.RED, pulsing=False)
            self._state_lbl.setText(inactive_text)
            self._state_lbl.setStyleSheet("color: #e05555; font-size: 11px;")


# ─────────────────────────────────────────────────────────────────────────────
# Main window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tina  ·  Bible Listener for EasyWorship")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(DARK_STYLESHEET)

        self._signals = BackendSignals()
        self._worker: Optional[BackendWorker] = None
        self._resend_workers: list = []
        self._session_start: Optional[float] = None
        self._is_running = False
        self._monitor_window: Optional[VerseMonitorWindow] = None

        self._build_ui()
        self._connect_signals()
        self._restore_window_state()

        # Session timer tick
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_timer)

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────
        self._sidebar = self._build_sidebar()
        root.addWidget(self._sidebar)

        # ── Main area ─────────────────────────────────────────────────────
        self._tabs = self._build_tabs()
        root.addWidget(self._tabs, stretch=1)

        # ── Status bar ────────────────────────────────────────────────────
        sb = QStatusBar()
        sb.setStyleSheet(
            "QStatusBar { background: #0a0a0f; color: #4a4a5a; "
            "font-size: 11px; border-top: 1px solid #1e1e2e; }"
        )
        self.setStatusBar(sb)
        self._sb_label = QLabel("Ready  ·  Simulation mode (backend not found)")
        sb.addWidget(self._sb_label)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(0)

        # Logo / name
        logo_area = QWidget()
        logo_layout = QVBoxLayout(logo_area)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(2)

        title_lbl = QLabel("TINA")
        title_lbl.setObjectName("appTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(title_lbl)

        subtitle_lbl = QLabel("BIBLE LISTENER")
        subtitle_lbl.setObjectName("appSubtitle")
        subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(subtitle_lbl)

        layout.addWidget(logo_area)
        layout.addSpacing(4)

        # Gold divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.HLine)
        div1.setStyleSheet("background: #c9a84c; max-height: 1px; margin: 0 8px;")
        layout.addWidget(div1)
        layout.addSpacing(20)

        # START / STOP button
        self._toggle_btn = QPushButton("▶  START LISTENING")
        self._toggle_btn.setObjectName("startButton")
        self._toggle_btn.setCheckable(False)
        self._toggle_btn.clicked.connect(self._toggle_listening)
        layout.addWidget(self._toggle_btn)
        layout.addSpacing(24)

        # Status panel
        status_panel = QWidget()
        status_panel.setObjectName("statusPanel")
        sp_layout = QVBoxLayout(status_panel)
        sp_layout.setContentsMargins(10, 10, 10, 10)
        sp_layout.setSpacing(8)

        status_title = QLabel("CONNECTION STATUS")
        status_title.setObjectName("statusTitle")
        sp_layout.addWidget(status_title)

        self._mic_row       = StatusRow("Microphone")
        self._ew_row        = StatusRow("EasyWorship")
        self._companion_row = StatusRow("Companion TCP")
        sp_layout.addWidget(self._mic_row)
        sp_layout.addWidget(self._ew_row)
        sp_layout.addWidget(self._companion_row)

        layout.addWidget(status_panel)
        layout.addSpacing(20)

        # Model info
        model_panel = QWidget()
        model_panel.setObjectName("statusPanel")
        mp_layout = QVBoxLayout(model_panel)
        mp_layout.setContentsMargins(10, 10, 10, 10)
        mp_layout.setSpacing(4)

        ml = QLabel("WHISPER MODEL")
        ml.setObjectName("statusTitle")
        mp_layout.addWidget(ml)

        self._model_label = QLabel("base")
        self._model_label.setStyleSheet("color: #c9a84c; font-size: 13px; font-weight: 600;")
        mp_layout.addWidget(self._model_label)
        layout.addWidget(model_panel)
        layout.addSpacing(20)

        # Timer
        timer_panel = QWidget()
        timer_panel.setObjectName("statusPanel")
        tp_layout = QVBoxLayout(timer_panel)
        tp_layout.setContentsMargins(10, 10, 10, 10)
        tp_layout.setSpacing(2)

        tc = QLabel("SESSION TIME")
        tc.setObjectName("statusTitle")
        tp_layout.addWidget(tc)

        self._timer_label = QLabel("00:00:00")
        self._timer_label.setObjectName("timerLabel")
        self._timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tp_layout.addWidget(self._timer_label)

        layout.addWidget(timer_panel)

        layout.addStretch()

        # Monitor window toggle
        monitor_btn = QPushButton("📺  Verse Monitor")
        monitor_btn.setToolTip("Open floating verse display (for second monitor)")
        monitor_btn.clicked.connect(self._toggle_monitor_window)
        layout.addWidget(monitor_btn)
        layout.addSpacing(8)

        # Version
        ver = QLabel("v1.0.0  ·  Tina")
        ver.setStyleSheet("color: #2a2a3a; font-size: 10px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        return sidebar

    def _build_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        # Tab 1 — Live Feed
        self._live_feed = LiveFeedWidget()
        tabs.addTab(self._live_feed, "  Live Feed  ")

        # Tab 2 — Verse History
        self._verse_history = VerseHistoryWidget()
        self._verse_history.resend_requested.connect(self._on_resend_requested)
        tabs.addTab(self._verse_history, "  Verse History  ")

        # Tab 3 — Settings
        self._settings = SettingsPanel()
        self._settings.settings_saved.connect(self._on_settings_saved)
        tabs.addTab(self._settings, "  Settings  ")

        return tabs

    # ── Signal wiring ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        s = self._signals
        s.transcript_received.connect(self._live_feed.append_transcript)
        s.verse_detected.connect(self._live_feed.highlight_verse)
        s.verse_detected.connect(self._verse_history.add_verse)
        s.verse_displayed.connect(self._verse_history.update_status)
        s.command_detected.connect(self._live_feed.highlight_command)
        s.mic_status_changed.connect(self._on_mic_status)
        s.ew_status_changed.connect(self._on_ew_status)
        s.companion_status_changed.connect(self._on_companion_status)
        s.started.connect(self._on_backend_started)
        s.stopped.connect(self._on_backend_stopped)
        s.error_occurred.connect(self._on_backend_error)

    # ── Listening toggle ───────────────────────────────────────────────────

    def _toggle_listening(self) -> None:
        if self._is_running:
            self._stop_listening()
        else:
            self._start_listening()

    def _start_listening(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._worker = BackendWorker(self._signals, self)
        self._worker.start()

        self._toggle_btn.setText("■  STOP LISTENING")
        self._toggle_btn.setObjectName("stopButton")
        self._toggle_btn.setStyle(self._toggle_btn.style())  # force re-polish
        self._is_running = True
        self._session_start = time.time()
        self._timer.start()
        self._live_feed.set_listening(True)
        self._sb_label.setText("Running…  Listening for Bible references")

    def _stop_listening(self) -> None:
        if self._worker:
            self._worker.request_stop()
            self._worker.wait(3000)

        self._toggle_btn.setText("▶  START LISTENING")
        self._toggle_btn.setObjectName("startButton")
        self._toggle_btn.setStyle(self._toggle_btn.style())
        self._is_running = False
        self._timer.stop()
        self._live_feed.set_listening(False)
        self._sb_label.setText("Stopped")

    # ── Backend event handlers ─────────────────────────────────────────────

    @pyqtSlot(bool)
    def _on_mic_status(self, active: bool) -> None:
        self._mic_row.set_ok(active, "Active", "Inactive")

    @pyqtSlot(bool)
    def _on_ew_status(self, connected: bool) -> None:
        self._ew_row.set_ok(connected, "Detected", "Not found")

    @pyqtSlot(bool)
    def _on_companion_status(self, connected: bool) -> None:
        self._companion_row.set_ok(connected, "Connected", "Offline")

    @pyqtSlot()
    def _on_backend_started(self) -> None:
        self._sb_label.setText("Backend running")

    @pyqtSlot()
    def _on_backend_stopped(self) -> None:
        self._mic_row.set_ok(False, inactive_text="Inactive")
        self._sb_label.setText("Backend stopped")

    @pyqtSlot(str)
    def _on_backend_error(self, msg: str) -> None:
        self._sb_label.setText(f"Error: {msg}")
        QMessageBox.critical(self, "Backend Error", msg)

    # ── Resend ────────────────────────────────────────────────────────────

    @pyqtSlot(str)
    def _on_resend_requested(self, ref_display: str) -> None:
        worker = ResendWorker(ref_display, self)
        worker.finished.connect(
            lambda ok, ref: self._verse_history.set_resend_result(ok, ref)
        )
        worker.finished.connect(
            lambda ok, ref: self._sb_label.setText(
                f"Resent {ref} → {'OK' if ok else 'FAILED'}"
            )
        )
        self._resend_workers.append(worker)
        worker.start()

    # ── Settings ──────────────────────────────────────────────────────────

    @pyqtSlot(dict)
    def _on_settings_saved(self, data: dict) -> None:
        model = data.get("whisper", {}).get("model", "base")
        self._model_label.setText(model)
        self._sb_label.setText("Settings saved")

    # ── Timer ─────────────────────────────────────────────────────────────

    def _tick_timer(self) -> None:
        if self._session_start is None:
            return
        elapsed = int(time.time() - self._session_start)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self._timer_label.setText(f"{h:02d}:{m:02d}:{s:02d}")

    # ── Monitor window ─────────────────────────────────────────────────────

    def _toggle_monitor_window(self) -> None:
        if self._monitor_window is None or not self._monitor_window.isVisible():
            if self._monitor_window is None:
                self._monitor_window = VerseMonitorWindow()
                # Wire verse events to monitor
                self._signals.verse_detected.connect(self._monitor_window.show_verse)
                self._signals.verse_displayed.connect(self._monitor_window.on_verse_displayed)
            self._monitor_window.show()
            self._monitor_window.raise_()
        else:
            self._monitor_window.hide()

    # ── Window state persistence ───────────────────────────────────────────

    def _restore_window_state(self) -> None:
        s = QSettings("TinaBibleListener", "MainWindow")
        geo = s.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        state = s.value("windowState")
        if state:
            self.restoreState(state)
        # Restore model label
        model = s.value("lastModel", "base")
        self._model_label.setText(str(model))

    def closeEvent(self, event) -> None:
        # Stop backend
        if self._is_running:
            self._stop_listening()

        # Save state
        s = QSettings("TinaBibleListener", "MainWindow")
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())
        s.setValue("lastModel", self._model_label.text())

        # Close monitor
        if self._monitor_window:
            self._monitor_window.close()

        super().closeEvent(event)
