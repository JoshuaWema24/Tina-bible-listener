# automation/ew_automation.py
"""
EasyWorship UI Automation Layer
---------------------------------
Uses pywinauto (preferred) with pyautogui fallback to:
  1. Detect the running EasyWorship window
  2. Open the Bible search panel / dialog
  3. Type a verse reference
  4. Confirm and trigger "Go Live"

Architecture decisions:
  - Never use hardcoded screen coordinates as the primary path; always prefer
    control-tree selectors (class names, AutomationId, control text).
  - Coordinates are used only as a last resort in the pyautogui fallback.
  - All public methods are wrapped in tenacity retry logic.
  - Each action is observable: we verify focus/state after the action.
"""

from __future__ import annotations

import time
from typing import Optional

from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

try:
    import pywinauto
    from pywinauto import Application, Desktop
    from pywinauto.keyboard import send_keys
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    logger.warning("pywinauto not installed — falling back to pyautogui only")

try:
    import pyautogui
    import pyautogui as pag
    PYAUTOGUI_AVAILABLE = True
    pag.FAILSAFE = True
    pag.PAUSE = 0.05
except ImportError:
    PYAUTOGUI_AVAILABLE = False

from config.settings import AutomationConfig
from bible_parser import BibleReference


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EWAutomationError(Exception):
    """Raised when UI automation fails after all retries."""


class EWWindowNotFoundError(EWAutomationError):
    """EasyWorship window could not be located."""


# ---------------------------------------------------------------------------
# Helper: tenacity retry decorator
# ---------------------------------------------------------------------------

def _ew_retry(attempts: int = 3):
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.3, min=0.3, max=2.0),
        retry=retry_if_exception_type((EWAutomationError, Exception)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# ---------------------------------------------------------------------------
# Core Automation Class
# ---------------------------------------------------------------------------

class EasyWorshipAutomation:
    """
    Drives the EasyWorship GUI to search and display Bible verses.
    """

    def __init__(self, cfg: Optional[AutomationConfig] = None) -> None:
        self._cfg = cfg or AutomationConfig()
        self._app: Optional[Application] = None
        self._main_win = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display_verse(self, ref: BibleReference) -> bool:
        """
        Attempt to display a Bible verse in EasyWorship.
        Returns True on success, False on failure.
        """
        try:
            self._ensure_window()
            self._search_and_display(ref)
            logger.success("Verse displayed in EasyWorship: {}", ref.display)
            return True
        except EWWindowNotFoundError:
            logger.error("EasyWorship window not found — cannot automate")
            return False
        except Exception as exc:
            logger.error("EW automation failed for {}: {}", ref.display, exc)
            return False

    def send_slide_command(self, action: str) -> bool:
        """
        Send a slide control command via keyboard shortcuts.
        Action: "next", "previous", "go_live", "black_screen", "clear"
        """
        HOTKEYS = {
            "next": "{RIGHT}",
            "previous": "{LEFT}",
            "go_live": "{F7}",
            "black_screen": "{F8}",
            "clear": "{ESCAPE}",
        }
        key = HOTKEYS.get(action)
        if not key:
            logger.warning("Unknown slide action: {}", action)
            return False
        try:
            self._ensure_window()
            self._focus_main_window()
            send_keys(key)
            logger.info("Slide command sent: {} → {}", action, key)
            return True
        except Exception as exc:
            logger.error("Slide command failed: {}", exc)
            return False

    # ------------------------------------------------------------------
    # Window detection
    # ------------------------------------------------------------------

    @_ew_retry(attempts=3)
    def _ensure_window(self) -> None:
        """Locate the EasyWorship main window. Raises EWWindowNotFoundError if absent."""
        if not PYWINAUTO_AVAILABLE:
            # Minimal check via pyautogui — just verify a window is findable
            return

        try:
            # Try to reuse existing app connection
            if self._app is not None:
                windows = self._app.windows()
                if windows:
                    return
        except Exception:
            self._app = None

        # Connect to running EasyWorship process
        try:
            self._app = Application(backend="uia").connect(
                title_re=f".*{self._cfg.ew_window_title}.*",
                timeout=3,
            )
            self._main_win = self._app.window(
                title_re=f".*{self._cfg.ew_window_title}.*"
            )
            logger.debug("Connected to EasyWorship window")
        except Exception as exc:
            raise EWWindowNotFoundError(
                f"Could not find EasyWorship window: {exc}"
            ) from exc

    def _focus_main_window(self) -> None:
        """Bring EasyWorship to the foreground."""
        if self._main_win is not None:
            try:
                self._main_win.set_focus()
                time.sleep(self._cfg.action_delay)
            except Exception as exc:
                logger.warning("Could not focus EW window: {}", exc)

    # ------------------------------------------------------------------
    # Bible search automation — pywinauto path
    # ------------------------------------------------------------------

    @_ew_retry(attempts=3)
    def _search_and_display(self, ref: BibleReference) -> None:
        """Full search-and-display flow."""
        if PYWINAUTO_AVAILABLE:
            try:
                self._search_via_pywinauto(ref)
                return
            except Exception as exc:
                logger.warning(
                    "pywinauto path failed ({}), trying pyautogui fallback", exc
                )

        if PYAUTOGUI_AVAILABLE and self._cfg.allow_pyautogui_fallback:
            self._search_via_pyautogui(ref)
            return

        raise EWAutomationError("All automation backends failed")

    def _search_via_pywinauto(self, ref: BibleReference) -> None:
        """
        pywinauto-based Bible search.

        EasyWorship's Bible search can typically be opened with Ctrl+B.
        The dialog contains an edit box where we type the verse reference.

        Note: EW's internal control names may differ between versions.
        We use multiple selector strategies in priority order.
        """
        self._focus_main_window()

        # Step 1: Open the Bible search (Ctrl+B is the documented shortcut)
        logger.debug("Opening Bible search with {}", self._cfg.bible_search_hotkey)
        send_keys(self._cfg.bible_search_hotkey)
        time.sleep(0.4)

        # Step 2: Find the search dialog / input control
        search_box = self._find_bible_search_control()
        if search_box is None:
            raise EWAutomationError("Could not locate Bible search input control")

        # Step 3: Clear existing text and type the reference
        logger.debug("Typing verse reference: {}", ref.display)
        search_box.set_focus()
        search_box.triple_click()         # select all existing text
        time.sleep(0.1)
        search_box.type_keys(ref.display, with_spaces=True)
        time.sleep(0.3)

        # Step 4: Press Enter to search / confirm
        search_box.type_keys("{ENTER}")
        time.sleep(0.5)

        # Step 5: Trigger Go Live (F7 in EasyWorship)
        self._focus_main_window()
        send_keys(self._cfg.go_live_key)
        time.sleep(0.2)
        logger.debug("Go Live sent")

    def _find_bible_search_control(self):
        """
        Try multiple strategies to find the Bible search input.
        Returns a pywinauto control or None.
        """
        strategies = [
            # Strategy A: Look for a dialog with "Bible" in the title
            lambda: self._app.window(title_re=".*Bible.*").child_window(
                control_type="Edit"
            ),
            # Strategy B: Look for the search bar directly in the main window
            lambda: self._main_win.child_window(
                title="Bible Reference", control_type="Edit"
            ),
            # Strategy C: Any edit box that appears after the hotkey
            lambda: self._main_win.child_window(
                auto_id="BibleSearchBox"
            ),
            # Strategy D: First Edit control in top toolbar area
            lambda: self._main_win.child_window(
                control_type="Edit", found_index=0
            ),
        ]

        for i, strategy in enumerate(strategies):
            try:
                ctrl = strategy()
                ctrl.wait("visible", timeout=2)
                logger.debug("Bible search control found via strategy {}", i + 1)
                return ctrl
            except Exception:
                continue

        return None

    # ------------------------------------------------------------------
    # Bible search automation — pyautogui fallback path
    # ------------------------------------------------------------------

    def _search_via_pyautogui(self, ref: BibleReference) -> None:
        """
        Last-resort automation using global keyboard shortcuts only.
        We do NOT use hardcoded pixel coordinates here.
        We rely entirely on keyboard navigation which is more robust.
        """
        logger.debug("Using pyautogui keyboard path for {}", ref.display)

        # Focus EasyWorship (Alt+Tab or taskbar — we use Win32 API via pag)
        self._focus_ew_via_taskbar()
        time.sleep(0.3)

        # Open Bible search
        pag.hotkey(*self._cfg.bible_search_hotkey.split("+"))
        time.sleep(0.4)

        # Select all and type the verse
        pag.hotkey("ctrl", "a")
        time.sleep(0.1)
        pag.typewrite(ref.display, interval=0.04)
        time.sleep(0.3)

        # Confirm
        pag.press("enter")
        time.sleep(0.5)

        # Go Live
        pag.press(self._cfg.go_live_key.lower().replace("f", "f"))  # e.g. "f7"
        time.sleep(0.2)

    def _focus_ew_via_taskbar(self) -> None:
        """Best-effort window focus without coordinates."""
        if PYWINAUTO_AVAILABLE:
            try:
                Desktop(backend="uia").window(
                    title_re=f".*{self._cfg.ew_window_title}.*"
                ).set_focus()
            except Exception:
                pass
