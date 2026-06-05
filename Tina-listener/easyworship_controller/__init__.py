"""
EasyWorship Controller Package Init
------------------------------------
Wires together all core components of Tina's control layer.
"""

from loguru import logger

# ✅ IMPORTANT: ensure correct imports
from .action_router import ActionRouter
from .decision_engine import DecisionEngine
from .companion_client import CompanionClient
from automation.ew_automation import EasyWorshipAutomation
from overlay.verse_overlay import VerseOverlay


class EasyWorshipController:
    """
    Main entry point that binds all EW-related systems together.
    """

    def __init__(self, cfg):
        self._cfg = cfg

        # -----------------------------
        # CORE COMPONENTS
        # -----------------------------
        self._automation = EasyWorshipAutomation(cfg.automation)
        self._overlay = VerseOverlay(cfg.overlay)
        self._companion = CompanionClient(cfg.companion)
        self._decision_engine = DecisionEngine(cfg.engine)

        # -----------------------------
        # ACTION ROUTER (THE FIX)
        # -----------------------------
        self._router = ActionRouter()

        # Register subsystems safely
        self._router.register_easyworship(self._automation)
        self._router.register_overlay(self._overlay)
        self._router.register_companion(self._companion)

        logger.success("EasyWorshipController initialized successfully")

    # -----------------------------
    # OPTIONAL START/STOP METHODS
    # -----------------------------

    def start(self):
        logger.info("Starting EasyWorship Controller...")

        self._overlay.start()
        self._companion.connect()

        logger.success("Controller is running")

    def stop(self):
        logger.info("Stopping EasyWorship Controller...")

        self._overlay.stop()
        self._companion.disconnect()

        logger.success("Controller stopped")