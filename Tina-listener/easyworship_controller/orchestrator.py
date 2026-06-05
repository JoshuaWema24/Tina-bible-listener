from __future__ import annotations

import queue
import threading
import time
from typing import Optional, Callable, Any

from loguru import logger

from bible_parser import BibleReference
from config.settings import CONFIG, AppConfig

from easyworship_controller.decision_engine import DecisionEngine, IntentType
from easyworship_controller.companion_client import CompanionClient
from easyworship_controller.action_router import ActionRouter
from automation.ew_automation import EasyWorshipAutomation
from overlay.verse_overlay import VerseOverlay
from speech.capture import SpeechCapture, TranscriptSegment


class Orchestrator:
    """
    Central brain of Tina (backend-only, UI-agnostic).

    Now upgraded to:
    - Emit UI events via callbacks (for PyQt6 integration)
    - Safer threading
    - Better failure isolation
    """

    def __init__(self, cfg: Optional[AppConfig] = None) -> None:
        self._cfg = cfg or CONFIG

        # -----------------------------
        # Event callbacks (UI hooks)
        # -----------------------------
        self.on_transcript: Optional[Callable[[str, str], None]] = None
        self.on_verse_detected: Optional[Callable[[str, float, bool], None]] = None
        self.on_verse_displayed: Optional[Callable[[str, str], None]] = None
        self.on_command_detected: Optional[Callable[[str], None]] = None
        self.on_ew_status: Optional[Callable[[bool], None]] = None

        # -----------------------------
        # Core queue + lifecycle
        # -----------------------------
        self._work_queue: queue.Queue[TranscriptSegment] = queue.Queue(
            maxsize=self._cfg.engine.queue_max_size
        )

        self._running = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # -----------------------------
        # Backend modules
        # -----------------------------
        self._decision_engine = DecisionEngine(self._cfg.engine)
        self._companion = CompanionClient(self._cfg.companion)
        self._automation = EasyWorshipAutomation(self._cfg.automation)
        self._overlay = VerseOverlay(self._cfg.overlay)
        self._router = ActionRouter()
        self._capture = SpeechCapture(
            on_transcript=self._on_transcript,
            audio_cfg=self._cfg.audio,
            whisper_cfg=self._cfg.whisper,
        )

    # =========================================================
    # LIFECYCLE
    # =========================================================

    def start(self) -> None:
        logger.info("Starting Tina Orchestrator...")

        self._running.set()

        # Start overlay (separate GUI thread)
        self._overlay.start()

        # Connect Companion (non-blocking)
        connected = self._companion.connect()
        self._emit_ew_status(connected)

        self._companion.start_auto_reconnect()

        # Worker thread
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="tina-orchestrator-worker",
            daemon=True,
        )
        self._worker_thread.start()

        # Speech capture (blocks until stop)
        logger.success("Tina is now listening 🎤")
        self._capture.start()

    def stop(self) -> None:
        logger.info("Stopping Tina...")

        self._running.clear()

        self._capture.stop()
        self._work_queue.put(None)

        if self._worker_thread:
            self._worker_thread.join(timeout=5)

        self._overlay.stop()
        self._companion.disconnect()

        logger.success("Tina stopped cleanly.")

    # =========================================================
    # SPEECH CALLBACK
    # =========================================================

    def _on_transcript(self, segment: TranscriptSegment) -> None:
        """Called from STT thread — MUST NEVER BLOCK."""
        try:
            self._work_queue.put_nowait(segment)

            if self.on_transcript:
                self.on_transcript(segment.text, segment.timestamp)

        except queue.Full:
            logger.warning("Queue full — dropping transcript chunk")

    # =========================================================
    # WORKER LOOP
    # =========================================================

    def _worker_loop(self) -> None:
        while self._running.is_set():
            try:
                segment = self._work_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if segment is None:
                break

            self._process(segment)

    def _process(self, segment: TranscriptSegment) -> None:
        start = time.monotonic()

        result = self._decision_engine.evaluate(segment.text)

        # -------------------------
        # NOISE
        # -------------------------
        if result.intent == IntentType.NOISE:
            return

        # -------------------------
        # COMMAND
        # -------------------------
        if result.intent == IntentType.COMMAND and result.command:
            action = result.command.action

            logger.info("Command detected: {}", action)

            if self.on_command_detected:
                self.on_command_detected(action)

            self._handle_command(action)
            return

        # -------------------------
        # VERSE
        # -------------------------
        if result.intent == IntentType.VERSE:
            for ref in result.references:
                self._handle_verse(ref, result.is_correction)

        logger.debug("Processed in {:.1f}ms",
                     (time.monotonic() - start) * 1000)

    # =========================================================
    # VERSE HANDLING
    # =========================================================

    def _handle_verse(self, ref: BibleReference, is_correction: bool) -> None:
        logger.info("Verse detected: {}", ref.display)

        confidence = getattr(ref, "confidence", 1.0)

        # UI event: detected
        if self.on_verse_detected:
            self.on_verse_detected(ref.display, confidence, is_correction)

        # Always show overlay (fallback visual layer)
        if self._cfg.overlay.always_show:
            self._overlay.show_verse(ref, self._get_verse_text(ref))

        # Try EasyWorship
        success = self._automation.display_verse(ref)

        if success:
            msg = "ew_success"
            logger.success("Verse shown in EasyWorship: {}", ref.display)
        else:
            msg = "failed"
            logger.warning("EW automation failed → fallback overlay used")

            # Ensure fallback is visible
            self._overlay.show_verse(ref, self._get_verse_text(ref))

        # UI event: displayed result
        if self.on_verse_displayed:
            self.on_verse_displayed(ref.display, msg)

    # =========================================================
    # COMMAND HANDLING
    # =========================================================

    def _handle_command(self, action: str) -> None:
        cmd = self._companion.action_to_command(action)

        # Try Companion TCP first
        if cmd and self._companion.send_command(cmd):
            logger.success("Sent via Companion: {}", action)
            return

        logger.warning("Companion failed → UI automation fallback")
        self._automation.send_slide_command(action)

    # =========================================================
    # UTIL
    # =========================================================

    def _get_verse_text(self, ref: BibleReference) -> str:
        return f"{ref.display} (verse text not yet integrated)"

    # =========================================================
    # INTERNAL STATUS EMITTERS
    # =========================================================

    def _emit_ew_status(self, connected: bool) -> None:
        if self.on_ew_status:
            self.on_ew_status(connected)