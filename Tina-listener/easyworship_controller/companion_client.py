# easyworship_controller/companion_client.py
"""
EasyWorship Companion TCP Client
----------------------------------
Handles the official Companion protocol for slide/media/schedule control.
Bible search is NOT available via Companion — that is handled by ew_automation.py.

The Companion protocol is text-based over TCP on port 7979.
Commands are newline-delimited strings.

Known commands (from EasyWorship Companion documentation):
  NEXT_SLIDE
  PREVIOUS_SLIDE
  GO_LIVE
  BLACK_SCREEN
  CLEAR_SCREEN
  LOGO
  GET_SCHEDULE_ITEM_LIST
  GET_CURRENT_ITEM
"""

from __future__ import annotations

import asyncio
import socket
import threading
import time
from typing import Callable, Optional

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from config.settings import CompanionConfig


# ---------------------------------------------------------------------------
# Command constants
# ---------------------------------------------------------------------------

class EWCommand:
    NEXT_SLIDE = "NEXT_SLIDE"
    PREVIOUS_SLIDE = "PREVIOUS_SLIDE"
    GO_LIVE = "GO_LIVE"
    BLACK_SCREEN = "BLACK_SCREEN"
    CLEAR_SCREEN = "CLEAR_SCREEN"
    LOGO = "LOGO"


# ---------------------------------------------------------------------------
# Synchronous TCP client (used from the main thread via run_in_executor)
# ---------------------------------------------------------------------------

class CompanionClient:
    """
    Thread-safe synchronous TCP client for EasyWorship Companion protocol.
    Maintains a persistent connection with auto-reconnect.
    """

    def __init__(self, cfg: Optional[CompanionConfig] = None) -> None:
        self._cfg = cfg or CompanionConfig()
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._connected = False
        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Attempt to connect to EasyWorship Companion. Returns True on success."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(3.0)
            self._sock.connect((self._cfg.host, self._cfg.port))
            self._sock.settimeout(None)
            self._connected = True
            logger.success(
                "Connected to EasyWorship Companion at {}:{}",
                self._cfg.host,
                self._cfg.port,
            )
            return True
        except (socket.error, OSError) as exc:
            logger.warning("Companion connection failed: {}", exc)
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        self._connected = False

    def start_auto_reconnect(self) -> None:
        """Spawn a background thread that keeps trying to reconnect."""
        self._stop_event.clear()
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            name="companion-reconnect",
            daemon=True,
        )
        self._reconnect_thread.start()

    def _reconnect_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._connected:
                logger.info("Attempting Companion reconnect...")
                self.connect()
            time.sleep(self._cfg.reconnect_delay)

    # ------------------------------------------------------------------
    # Command sending
    # ------------------------------------------------------------------

    def send_command(self, command: str) -> bool:
        """
        Send a Companion command string.
        Returns True if sent successfully.
        """
        if not self._connected or self._sock is None:
            logger.warning("Companion not connected — skipping command: {}", command)
            return False

        with self._lock:
            try:
                payload = f"{command}\n".encode("utf-8")
                self._sock.sendall(payload)
                logger.debug("Companion command sent: {}", command)
                return True
            except (socket.error, OSError) as exc:
                logger.error("Failed to send Companion command: {}", exc)
                self._connected = False
                return False

    def action_to_command(self, action: str) -> Optional[str]:
        """Map decision engine action name → EW Companion command string."""
        mapping = {
            "next": EWCommand.NEXT_SLIDE,
            "previous": EWCommand.PREVIOUS_SLIDE,
            "go_live": EWCommand.GO_LIVE,
            "black_screen": EWCommand.BLACK_SCREEN,
            "clear": EWCommand.CLEAR_SCREEN,
        }
        return mapping.get(action)
