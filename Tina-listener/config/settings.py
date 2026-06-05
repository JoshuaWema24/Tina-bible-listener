# config/settings.py
"""
Central configuration for Tina Bible Listener.
All tuneable parameters live here — no magic numbers scattered through the code.
"""

from dataclasses import dataclass, field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AudioConfig:
    # Microphone device index (None = system default)
    device_index: Optional[int] = None
    # Sample rate — Whisper expects 16 kHz
    sample_rate: int = 16_000
    # Chunk size fed to the STT buffer (320ms of audio at 16kHz)
    chunk_frames: int = 5_120
    # VAD energy threshold (0-1); lower = more sensitive
    vad_threshold: float = 0.02
    # Seconds of silence before we finalise a speech segment
    silence_timeout: float = 1.2
    # Maximum recording window before forced flush (seconds)
    max_segment_seconds: float = 8.0


@dataclass
class WhisperConfig:
    # Options: "tiny", "base", "small", "medium", "large-v3"
    model_size: str = "base"
    # "cuda" if GPU available, else "cpu"
    device: str = "cpu"
    # "float16" on GPU, "int8" on CPU for speed
    compute_type: str = "int8"
    language: str = "en"
    # Beam size (lower = faster, slightly less accurate)
    beam_size: int = 3
    # Prefix hint to help Whisper spot scripture references
    initial_prompt: str = (
        "Scripture references include books like Genesis, Exodus, Psalms, Proverbs, "
        "Matthew, Mark, Luke, John, Romans, Corinthians, Revelation."
    )


@dataclass
class CompanionConfig:
    host: str = field(default_factory=lambda: os.getenv("EW_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("EW_PORT", "7979")))
    # Seconds to wait before reconnect attempt
    reconnect_delay: float = 3.0


@dataclass
class AutomationConfig:
    # Partial title of the EasyWorship main window
    ew_window_title: str = "EasyWorship"
    # Seconds to wait after sending keystrokes before verifying
    action_delay: float = 0.25
    # How many times to retry a failed UI action
    max_retries: int = 3
    # Whether to fall back to pyautogui if pywinauto fails
    allow_pyautogui_fallback: bool = True
    # Coordinates are last-resort only; prefer control-based selectors
    bible_search_hotkey: str = "ctrl+b"          # EW shortcut to open Bible search
    search_box_title: str = "Bible Reference"    # Expected window/dialog title
    go_live_key: str = "F7"                      # EW "Go Live" hotkey


@dataclass
class OverlayConfig:
    # Show overlay even when EasyWorship automation succeeds (monitoring view)
    always_show: bool = True
    # Verse display duration in seconds (0 = manual dismiss)
    display_seconds: float = 0.0
    font_name: str = "Georgia"
    font_size: int = 42
    background_color: str = "#0a0a1a"
    text_color: str = "#f0e6d3"
    accent_color: str = "#c9a84c"
    window_width: int = 900
    window_height: int = 220
    # Screen edge: "top", "bottom"
    screen_edge: str = "bottom"
    opacity: float = 0.92


@dataclass
class EngineConfig:
    # Minimum confidence (0-1) before we act on a detection
    min_confidence: float = 0.65
    # Ignore the same verse if re-spoken within N seconds
    debounce_seconds: float = 6.0
    # Max queue depth for pending verse displays
    queue_max_size: int = 5


@dataclass
class AppConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    companion: CompanionConfig = field(default_factory=CompanionConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    log_dir: str = "logs"
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "0") == "1")


# Singleton — import this everywhere
CONFIG = AppConfig()
