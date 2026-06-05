#!/usr/bin/env python3
# main.py
"""
Tina Bible Listener for EasyWorship
======================================
Main entry point.

Usage:
    python main.py                          # Run with defaults
    python main.py --model small            # Use larger Whisper model
    python main.py --device cuda            # GPU acceleration
    python main.py --debug                  # Verbose logging
    python main.py --list-devices           # Show audio input devices
    python main.py --test-parser "John 3:16"  # Test Bible parser only
"""

import signal
import sys
import time

import click

# Bootstrap path so sub-packages can import from project root
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logging_setup import setup_logging
from loguru import logger


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--model", default="base",
              type=click.Choice(["tiny", "base", "small", "medium", "large-v3"]),
              show_default=True, help="Whisper model size.")
@click.option("--device", default="cpu", type=click.Choice(["cpu", "cuda"]),
              show_default=True, help="Compute device for Whisper.")
@click.option("--audio-device", default=None, type=int,
              help="Microphone device index (default: system default).")
@click.option("--ew-host", default="127.0.0.1", show_default=True,
              help="EasyWorship Companion host.")
@click.option("--ew-port", default=7979, show_default=True,
              help="EasyWorship Companion port.")
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.option("--list-devices", is_flag=True, help="List audio input devices and exit.")
@click.option("--test-parser", default=None, metavar="TEXT",
              help="Run Bible parser on TEXT and exit (no audio).")
@click.option("--no-overlay", is_flag=True, help="Disable the fallback overlay window.")
def main(model, device, audio_device, ew_host, ew_port, debug,
         list_devices, test_parser, no_overlay):
    """Tina — Real-time Bible verse listener for EasyWorship."""

    setup_logging(debug=debug)

    # ------------------------------------------------------------------
    # Special modes
    # ------------------------------------------------------------------

    if list_devices:
        _list_audio_devices()
        return

    if test_parser:
        _test_parser_mode(test_parser)
        return

    # ------------------------------------------------------------------
    # Build config
    # ------------------------------------------------------------------
    from config.settings import (
        AppConfig, AudioConfig, WhisperConfig,
        CompanionConfig, OverlayConfig,
    )

    cfg = AppConfig(
        audio=AudioConfig(device_index=audio_device),
        whisper=WhisperConfig(model_size=model, device=device,
                              compute_type="float16" if device == "cuda" else "int8"),
        companion=CompanionConfig(host=ew_host, port=ew_port),
        overlay=OverlayConfig(always_show=not no_overlay),
        debug=debug,
    )

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------
    from easyworship_controller.orchestrator import Orchestrator

    orchestrator = Orchestrator(cfg)

    # Graceful shutdown on Ctrl+C / SIGTERM
    def _shutdown(sig, frame):
        logger.info("Shutdown signal received...")
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print_banner()

    try:
        orchestrator.start()
        # start() blocks until stop() is called
    except KeyboardInterrupt:
        orchestrator.stop()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _list_audio_devices() -> None:
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print("\nAvailable audio input devices:")
        print("-" * 50)
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                marker = "  [DEFAULT]" if i == sd.default.device[0] else ""
                print(f"  [{i:2d}] {dev['name']}{marker}")
        print()
    except ImportError:
        print("sounddevice not installed — run: pip install sounddevice")


def _test_parser_mode(text: str) -> None:
    from bible_parser import BibleReferenceParser
    parser = BibleReferenceParser()
    refs = parser.parse(text)
    if refs:
        print(f"\nDetected {len(refs)} reference(s):")
        for r in refs:
            print(f"  ✓ {r.display}  (confidence: {r.confidence:.2f})"
                  f"{'  [CORRECTION]' if r.is_correction else ''}")
    else:
        print(f"\nNo Bible references detected in: \"{text}\"")
    print()


def print_banner() -> None:
    banner = r"""
  ████████╗██╗███╗   ██╗ █████╗
     ██╔══╝██║████╗  ██║██╔══██╗
     ██║   ██║██╔██╗ ██║███████║
     ██║   ██║██║╚██╗██║██╔══██║
     ██║   ██║██║ ╚████║██║  ██║
     ╚═╝   ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝
  Bible Listener for EasyWorship
  ─────────────────────────────────
  Listening for scripture references...
  Press Ctrl+C to stop.
"""
    print(banner)


if __name__ == "__main__":
    main()
