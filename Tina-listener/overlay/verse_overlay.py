# overlay/verse_overlay.py
"""
Fallback Verse Overlay Window
-------------------------------
Displays the detected verse on screen when EasyWorship automation fails,
or as a monitoring view for the operator.

Uses tkinter (stdlib) for maximum compatibility — no extra deps needed.
Runs in its own thread with a message queue so the main thread never blocks.

Design: dark translucent strip pinned to the bottom of the primary monitor,
styled like a broadcast lower-third.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Optional

from loguru import logger

from bible_parser import BibleReference
from config.settings import OverlayConfig


# ---------------------------------------------------------------------------
# Messages to the overlay thread
# ---------------------------------------------------------------------------

class _ShowMsg:
    def __init__(self, ref: BibleReference, verse_text: str = "") -> None:
        self.ref = ref
        self.verse_text = verse_text

class _HideMsg:
    pass

class _QuitMsg:
    pass


# ---------------------------------------------------------------------------
# Overlay Window
# ---------------------------------------------------------------------------

class VerseOverlay:
    """
    Thread-safe overlay.  Call start() once, then show_verse() / hide().
    All tkinter calls happen inside the dedicated GUI thread.
    """

    def __init__(self, cfg: Optional[OverlayConfig] = None) -> None:
        self._cfg = cfg or OverlayConfig()
        self._queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None
        self._hide_job = None

    # ------------------------------------------------------------------
    # Public API (thread-safe)
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_gui, name="overlay-gui", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._queue.put(_QuitMsg())

    def show_verse(self, ref: BibleReference, verse_text: str = "") -> None:
        self._queue.put(_ShowMsg(ref, verse_text))

    def hide(self) -> None:
        self._queue.put(_HideMsg())

    # ------------------------------------------------------------------
    # GUI thread
    # ------------------------------------------------------------------

    def _run_gui(self) -> None:
        cfg = self._cfg
        self._root = tk.Tk()
        root = self._root

        # Window setup
        root.overrideredirect(True)         # no title bar
        root.attributes("-topmost", True)   # always on top
        root.attributes("-alpha", cfg.opacity)
        root.configure(bg=cfg.background_color)
        root.resizable(False, False)

        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()

        win_w = cfg.window_width
        win_h = cfg.window_height
        x = (screen_w - win_w) // 2
        y = screen_h - win_h - 40 if cfg.screen_edge == "bottom" else 40
        root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # Accent bar at top
        accent_bar = tk.Frame(root, bg=cfg.accent_color, height=4)
        accent_bar.pack(fill="x", side="top")

        # Reference label (book/chapter:verse)
        self._ref_label = tk.Label(
            root,
            text="",
            font=(cfg.font_name, 18, "bold"),
            fg=cfg.accent_color,
            bg=cfg.background_color,
            pady=6,
        )
        self._ref_label.pack(fill="x", padx=24)

        # Verse text label
        self._verse_label = tk.Label(
            root,
            text="",
            font=(cfg.font_name, cfg.font_size),
            fg=cfg.text_color,
            bg=cfg.background_color,
            wraplength=win_w - 48,
            justify="left",
            pady=8,
        )
        self._verse_label.pack(fill="both", expand=True, padx=24)

        # Start hidden
        root.withdraw()

        # Poll the message queue
        root.after(100, self._poll_queue)
        root.mainloop()

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                if isinstance(msg, _ShowMsg):
                    self._do_show(msg)
                elif isinstance(msg, _HideMsg):
                    self._do_hide()
                elif isinstance(msg, _QuitMsg):
                    self._root.quit()
                    return
        except queue.Empty:
            pass
        self._root.after(80, self._poll_queue)

    def _do_show(self, msg: _ShowMsg) -> None:
        cfg = self._cfg

        # Cancel any pending auto-hide
        if self._hide_job is not None:
            self._root.after_cancel(self._hide_job)
            self._hide_job = None

        self._ref_label.config(text=msg.ref.display)
        verse_text = msg.verse_text or "..."
        self._verse_label.config(text=verse_text)

        # Resize window to fit content
        self._root.update_idletasks()
        self._root.deiconify()
        logger.debug("Overlay shown: {}", msg.ref.display)

        # Auto-hide if configured
        if cfg.display_seconds > 0:
            self._hide_job = self._root.after(
                int(cfg.display_seconds * 1000), self._do_hide
            )

    def _do_hide(self) -> None:
        if self._root:
            self._root.withdraw()
        self._hide_job = None
