# speech/capture.py
"""
Real-time Speech Capture + STT
--------------------------------
Uses faster-whisper with a sliding VAD buffer.
Emits transcription segments via a callback as soon as speech ends.

Design choices:
- sounddevice for low-latency audio capture (lower overhead than pyaudio)
- Energy-based VAD to detect speech boundaries without extra dependencies
- Separate daemon thread for STT inference so the audio callback never blocks
- Whisper runs on the last N seconds of audio (not full history) for latency
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from loguru import logger

from config.settings import AudioConfig, WhisperConfig


@dataclass
class TranscriptSegment:
    text: str
    timestamp: float          # time.monotonic() at end of segment
    is_partial: bool = False  # True if we flushed early (max_segment timeout)


TranscriptCallback = Callable[[TranscriptSegment], None]


class SpeechCapture:
    """
    Capture audio from a microphone, detect speech segments via energy VAD,
    and emit transcribed text via a callback.

    Usage::

        def on_transcript(seg: TranscriptSegment):
            print(seg.text)

        cap = SpeechCapture(on_transcript=on_transcript)
        cap.start()
        ...
        cap.stop()
    """

    def __init__(
        self,
        on_transcript: TranscriptCallback,
        audio_cfg: Optional[AudioConfig] = None,
        whisper_cfg: Optional[WhisperConfig] = None,
    ) -> None:
        self._callback = on_transcript
        self._acfg = audio_cfg or AudioConfig()
        self._wcfg = whisper_cfg or WhisperConfig()

        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._running = threading.Event()

        # Rolling buffer of audio frames (numpy float32)
        self._buffer: list[np.ndarray] = []
        self._silence_frames = 0
        self._active_speech = False
        self._segment_start_time: float = 0.0

        logger.info(
            "Loading Whisper model '{}' ({}) on {}...",
            self._wcfg.model_size,
            self._wcfg.compute_type,
            self._wcfg.device,
        )
        self._model = WhisperModel(
            self._wcfg.model_size,
            device=self._wcfg.device,
            compute_type=self._wcfg.compute_type,
        )
        logger.success("Whisper model loaded.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start audio capture and STT background threads."""
        self._running.set()
        self._stt_thread = threading.Thread(
            target=self._stt_worker, name="stt-worker", daemon=True
        )
        self._stt_thread.start()

        self._stream = sd.InputStream(
            samplerate=self._acfg.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self._acfg.chunk_frames,
            device=self._acfg.device_index,
            callback=self._audio_callback,
        )
        self._stream.start()
        logger.info("Audio capture started (device={})", self._acfg.device_index)

    def stop(self) -> None:
        """Gracefully stop capture."""
        self._running.clear()
        self._stream.stop()
        self._stream.close()
        self._audio_queue.put(None)   # sentinel
        self._stt_thread.join(timeout=5)
        logger.info("Audio capture stopped.")

    # ------------------------------------------------------------------
    # Audio callback (runs in sounddevice's C thread — must be fast)
    # ------------------------------------------------------------------

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info,
        status,
    ) -> None:
        if status:
            logger.warning("Audio stream status: {}", status)
        # Enqueue a copy (indata is a view into a shared buffer)
        self._audio_queue.put_nowait(indata[:, 0].copy())

    # ------------------------------------------------------------------
    # STT worker thread
    # ------------------------------------------------------------------

    def _stt_worker(self) -> None:
        """
        Drain the audio queue, perform VAD, and run Whisper on completed segments.
        """
        sr = self._acfg.sample_rate
        silence_threshold_frames = int(
            self._acfg.silence_timeout * sr / self._acfg.chunk_frames
        )
        max_frames = int(
            self._acfg.max_segment_seconds * sr / self._acfg.chunk_frames
        )

        while self._running.is_set():
            try:
                chunk = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if chunk is None:
                break

            energy = float(np.sqrt(np.mean(chunk ** 2)))
            is_speech = energy > self._acfg.vad_threshold

            if is_speech:
                if not self._active_speech:
                    self._active_speech = True
                    self._segment_start_time = time.monotonic()
                    logger.debug("Speech start detected (energy={:.4f})", energy)
                self._silence_frames = 0
                self._buffer.append(chunk)
            else:
                if self._active_speech:
                    self._silence_frames += 1
                    self._buffer.append(chunk)   # keep trailing silence for Whisper

                    # Segment complete: silence timeout reached
                    if self._silence_frames >= silence_threshold_frames:
                        self._flush_buffer(is_partial=False)

            # Safety: flush if buffer too long (preacher speaks without pausing)
            if len(self._buffer) >= max_frames:
                self._flush_buffer(is_partial=True)

    def _flush_buffer(self, is_partial: bool) -> None:
        """Concatenate buffered audio and run Whisper inference."""
        if not self._buffer:
            return

        audio = np.concatenate(self._buffer)
        self._buffer.clear()
        self._active_speech = False
        self._silence_frames = 0

        duration = len(audio) / self._acfg.sample_rate
        if duration < 0.3:
            logger.debug("Skipping too-short segment ({:.2f}s)", duration)
            return

        logger.debug("Running STT on {:.2f}s segment...", duration)
        try:
            segments, _info = self._model.transcribe(
                audio,
                language=self._wcfg.language,
                beam_size=self._wcfg.beam_size,
                initial_prompt=self._wcfg.initial_prompt,
                vad_filter=False,   # we do our own VAD
            )
            text = " ".join(s.text for s in segments).strip()
            if text:
                logger.debug("Transcript: {}", text)
                self._callback(TranscriptSegment(
                    text=text,
                    timestamp=time.monotonic(),
                    is_partial=is_partial,
                ))
        except Exception as exc:
            logger.error("Whisper inference error: {}", exc)
