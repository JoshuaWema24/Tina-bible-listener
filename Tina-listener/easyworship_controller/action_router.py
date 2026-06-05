"""
ActionRouter
------------
Central dispatcher that takes high-level AI/decision actions
and routes them to the correct subsystem:

- EasyWorship automation
- Overlay system
- Companion TCP
"""

from loguru import logger


class ActionRouter:
    def __init__(self):
        self._ew = None
        self._overlay = None
        self._companion = None

    # -----------------------------
    # Registration methods
    # -----------------------------
    def register_easyworship(self, ew):
        self._ew = ew
        logger.info("EasyWorship automation registered")

    def register_overlay(self, overlay):
        self._overlay = overlay
        logger.info("Overlay system registered")

    def register_companion(self, companion):
        self._companion = companion
        logger.info("Companion client registered")

    # -----------------------------
    # HIGH LEVEL ACTION API
    # -----------------------------

    def handle(self, action: str, payload: dict = None):
        """
        Main entry point for all Tina actions.
        """

        payload = payload or {}

        logger.info(f"Routing action: {action} | payload={payload}")

        # ---------------- EASYWORSHIP ----------------
        if action == "show_verse":
            ref = payload.get("reference")
            if self._ew:
                return self._ew.display_verse(ref)

        if action == "next_slide":
            if self._companion:
                return self._companion.send_command("NEXT_SLIDE")

        if action == "prev_slide":
            if self._companion:
                return self._companion.send_command("PREV_SLIDE")

        # ---------------- OVERLAY ----------------
        if action == "overlay_show":
            if self._overlay:
                return self._overlay.show_verse(
                    payload.get("reference"),
                    payload.get("text", "")
                )

        # ---------------- FALLBACK ----------------
        logger.warning(f"No handler for action: {action}")
        return False