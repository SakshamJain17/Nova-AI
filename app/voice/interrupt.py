from __future__ import annotations

import threading
import time

import numpy as np
import sounddevice as sd

from .text_to_speech import (
    stop_speaking,
    is_speaking,
)


# ============================================================
# CONFIGURATION
# ============================================================

SAMPLE_RATE = 16000
BLOCK_SIZE = 1024

# This is intentionally conservative.
VOICE_THRESHOLD = 0.08

CHECK_INTERVAL = 0.05


# ============================================================
# STATE
# ============================================================

_running = False
_thread = None


# ============================================================
# MICROPHONE MONITOR
# ============================================================

def _monitor_microphone():

    global _running

    def audio_callback(
        indata,
        frames,
        time_info,
        status,
    ):

        if not _running:
            return

        # Only monitor while TTS is active.
        if not is_speaking():
            return

        try:

            volume = float(
                np.sqrt(
                    np.mean(
                        indata ** 2
                    )
                )
            )

        except Exception:

            return

        # IMPORTANT:
        #
        # This can detect ANY loud sound, including NOVA itself.
        #
        # Therefore keep threshold conservative.
        #

        if volume > VOICE_THRESHOLD:

            print(
                "\n[Voice detected — interrupt requested]"
            )

            try:

                stop_speaking()

            except Exception as error:

                print(
                    f"[INTERRUPT ERROR] {error}"
                )

    try:

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=BLOCK_SIZE,
            dtype="float32",
            callback=audio_callback,
        ):

            while _running:

                time.sleep(
                    CHECK_INTERVAL
                )

    except Exception as error:

        print(
            f"[INTERRUPT MONITOR ERROR] {error}"
        )


# ============================================================
# START
# ============================================================

def start_interrupt_monitor():

    global _running
    global _thread

    if _running:
        return

    _running = True

    _thread = threading.Thread(
        target=_monitor_microphone,
        daemon=True,
        name="NOVA-Interrupt-Monitor",
    )

    _thread.start()

    print(
        "[INTERRUPT] Monitor started."
    )


# ============================================================
# STOP
# ============================================================

def stop_interrupt_monitor():

    global _running

    _running = False

    print(
        "[INTERRUPT] Monitor stopped."
    )


# ============================================================
# STATUS
# ============================================================

def is_interrupt_monitor_running():

    return _running
