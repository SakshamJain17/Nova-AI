from __future__ import annotations

import os
import tempfile
import time
import wave

import numpy as np
import sounddevice as sd
import whisper


# ============================================================
# CONFIGURATION
# ============================================================

SAMPLE_RATE = 16000

# Maximum recording duration.
RECORD_SECONDS = 5

# Your MacBook Pro microphone.
INPUT_DEVICE = 1

MODEL_SIZE = "base"

# Time for speaker/microphone hardware to settle.
MIC_SETTLE_DELAY = 0.8

# Maximum time to wait for NOVA's TTS to finish.
MAX_TTS_WAIT = 30.0


# ============================================================
# LOAD WHISPER
# ============================================================

print("Loading NOVA speech recognition...")

model = whisper.load_model(
    MODEL_SIZE
)

print("Speech recognition ready.")


# ============================================================
# TTS STATE CHECK
# ============================================================

def nova_is_speaking() -> bool:
    """
    Check whether NOVA's TTS system is currently speaking.

    Returns False if the TTS module does not expose the
    is_speaking() function.
    """

    try:

        from app.voice.text_to_speech import is_speaking

        return bool(
            is_speaking()
        )

    except Exception:

        return False


# ============================================================
# WAIT UNTIL NOVA FINISHES SPEAKING
# ============================================================

def wait_for_nova_to_finish():

    start_time = time.monotonic()

    while nova_is_speaking():

        # Safety timeout.
        if (
            time.monotonic() - start_time
            > MAX_TTS_WAIT
        ):

            print(
                "[VOICE] TTS timeout; continuing."
            )

            break

        time.sleep(
            0.05
        )

    # Give the microphone/speaker system time to settle.
    time.sleep(
        MIC_SETTLE_DELAY
    )


# ============================================================
# RECORD AUDIO
# ============================================================

def record_audio():

    # --------------------------------------------------------
    # CRITICAL:
    # NEVER START RECORDING WHILE NOVA IS SPEAKING.
    # --------------------------------------------------------

    wait_for_nova_to_finish()

    print()
    print(
        "Listening..."
    )

    try:

        audio = sd.rec(
            int(
                RECORD_SECONDS
                * SAMPLE_RATE
            ),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=INPUT_DEVICE,
        )

        sd.wait()

        return audio.flatten()

    except Exception as error:

        print(
            f"[MIC ERROR] {error}"
        )

        return np.array(
            [],
            dtype=np.float32,
        )


# ============================================================
# SAVE WAV
# ============================================================

def save_audio(
    audio,
    filename,
):

    if audio is None or len(audio) == 0:
        return

    # Prevent clipping.
    audio = np.clip(
        audio,
        -1.0,
        1.0,
    )

    audio_int16 = np.int16(
        audio * 32767
    )

    with wave.open(
        filename,
        "wb",
    ) as file:

        file.setnchannels(1)

        file.setsampwidth(2)

        file.setframerate(
            SAMPLE_RATE
        )

        file.writeframes(
            audio_int16.tobytes()
        )


# ============================================================
# CHECK WHETHER AUDIO CONTAINS ACTUAL SOUND
# ============================================================

def has_audio(
    audio,
    threshold=0.008,
):

    if audio is None or len(audio) == 0:
        return False

    rms = float(
        np.sqrt(
            np.mean(
                np.square(audio)
            )
        )
    )

    return rms >= threshold


# ============================================================
# SPEECH RECOGNITION
# ============================================================

def listen():

    # --------------------------------------------------------
    # Wait for TTS to completely finish.
    # --------------------------------------------------------

    wait_for_nova_to_finish()

    # --------------------------------------------------------
    # Record
    # --------------------------------------------------------

    audio = record_audio()

    if audio is None or len(audio) == 0:

        return ""

    # --------------------------------------------------------
    # Ignore completely silent recordings.
    # --------------------------------------------------------

    if not has_audio(audio):

        print(
            "[VOICE] No speech detected."
        )

        return ""

    filename = None

    try:

        # ----------------------------------------------------
        # Temporary WAV
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as temp_file:

            filename = temp_file.name

        save_audio(
            audio,
            filename,
        )

        # ----------------------------------------------------
        # Whisper
        # ----------------------------------------------------

        result = model.transcribe(
            filename,
            language="en",
            task="transcribe",
            fp16=False,
            temperature=0,
            condition_on_previous_text=False,
        )

        text = result.get(
            "text",
            "",
        ).strip()

        # ----------------------------------------------------
        # Normalize whitespace.
        # ----------------------------------------------------

        text = " ".join(
            text.split()
        )

        if not text:

            return ""

        print(
            f"You: {text}"
        )

        return text

    except Exception as error:

        print(
            f"[STT ERROR] {error}"
        )

        return ""

    finally:

        if (
            filename
            and os.path.exists(filename)
        ):

            try:

                os.remove(filename)

            except OSError:

                pass
