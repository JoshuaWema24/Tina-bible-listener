"""
ui/backend_worker.py
Clean, production-safe Qt bridge for Tina Orchestrator.

Architecture:
Orchestrator (backend brain)
        ↓ callbacks
BackendWorker (Qt bridge thread)
        ↓ Qt signals
PyQt6 UI (dashboard)
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from typing import Optional
from bible_parser.parser import BibleReferenceParser
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from config.settings import CONFIG

# Backend import (safe fallback handled later if needed)
from easyworship_controller.orchestrator import Orchestrator


# =========================================================
# SIGNAL DEFINITIONS
# =========================================================
class BackendSignals(QObject):
    transcript_received = pyqtSignal(str, str)      # text, timestamp
    verse_detected = pyqtSignal(str, float, bool)   # ref, confidence, correction
    verse_displayed = pyqtSignal(str, str)          # ref, status
    command_detected = pyqtSignal(str)

    ew_status_changed = pyqtSignal(bool)
    mic_status_changed = pyqtSignal(bool)
    companion_status_changed = pyqtSignal(bool)

    error_occurred = pyqtSignal(str)
    started = pyqtSignal()
    stopped = pyqtSignal()


# =========================================================
# MAIN BACKEND WORKER
# =========================================================
class BackendWorker(QThread):
    """
    Qt thread wrapper around Orchestrator.

    Responsibilities:
    - Start/stop backend safely
    - Connect Orchestrator callbacks → Qt signals
    - Keep UI thread safe
    """

    def __init__(self, signals: BackendSignals, parent=None):
        super().__init__(parent)
        self.signals = signals
        self._orchestrator: Optional[Orchestrator] = None
        self._stop_event = threading.Event()

    # -----------------------------------------------------
    # THREAD ENTRY
    # -----------------------------------------------------
    def run(self) -> None:
        try:
            self._start_backend()
        except Exception as e:
            self.signals.error_occurred.emit(str(e))
        finally:
            self.signals.stopped.emit()

    # -----------------------------------------------------
    # STOP REQUEST
    # -----------------------------------------------------
    def request_stop(self) -> None:
        self._stop_event.set()

        if self._orchestrator:
            try:
                self._orchestrator.stop()
            except Exception:
                pass

    # -----------------------------------------------------
    # BACKEND START
    # -----------------------------------------------------
    def _start_backend(self) -> None:
        self._orchestrator = Orchestrator(CONFIG)

        # =================================================
        # CONNECT ORCHESTRATOR CALLBACKS → QT SIGNALS
        # =================================================

        self._orchestrator.on_transcript = self._handle_transcript
        self._orchestrator.on_verse_detected = self._handle_verse_detected
        self._orchestrator.on_verse_displayed = self._handle_verse_displayed
        self._orchestrator.on_command_detected = self._handle_command
        self._orchestrator.on_ew_status = self._handle_ew_status

        self.signals.started.emit()

        # BLOCKING CALL (runs full system)
        self._orchestrator.start()

    # =========================================================
    # CALLBACK HANDLERS
    # =========================================================

    def _handle_transcript(self, text: str, timestamp: str):
        self.signals.transcript_received.emit(
            text,
            timestamp or datetime.now().strftime("%H:%M:%S")
        )

    def _handle_verse_detected(self, ref: str, confidence: float, is_correction: bool):
        self.signals.verse_detected.emit(ref, confidence, is_correction)

    def _handle_verse_displayed(self, ref: str, status: str):
        self.signals.verse_displayed.emit(ref, status)

    def _handle_command(self, action: str):
        self.signals.command_detected.emit(action)

    def _handle_ew_status(self, connected: bool):
        self.signals.ew_status_changed.emit(connected)


# =========================================================
# RESEND WORKER (runs in background thread)
# =========================================================
class ResendWorker(QThread):
    """
    Re-sends a verse to EasyWorship without blocking UI.
    """

    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, ref_display: str, parent=None):
        super().__init__(parent)
        self.ref_display = ref_display

    def run(self):
        try:
            from bible_parser.parser import BibleReferenceParser
            from automation.ew_automation import EasyWorshipAutomation
            from config.settings import CONFIG

            time.sleep(0.2)  # small UX delay

            parser = BibleReferenceParser()
            refs = parser.parse(self.ref_display)

            if not refs:
                self.finished.emit(False, "Invalid Bible reference")
                return

            ew = EasyWorshipAutomation(CONFIG.automation)
            ok = ew.display_verse(refs[0])

            if ok:
                self.finished.emit(True, self.ref_display)
            else:
                self.finished.emit(False, "EasyWorship failed to display verse")

        except Exception as e:
            self.finished.emit(False, str(e))