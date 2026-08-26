from __future__ import annotations

"""
============================================================
NOVA — ADVANCED MACOS TEXT-TO-SPEECH ENGINE
============================================================

Features
--------
• Native macOS `say` engine
• Background speech
• Pause without losing generated speech
• Resume from the same position
• Stop immediately
• Thread-safe state management
• Speech queue
• Interrupt current speech
• Multiple voice support
• Adjustable speech rate
• Text preprocessing
• Long-text handling
• Sentence-aware queueing
• State callbacks
• Error recovery
• Self diagnostics
• Compatible with NOVA GUI
• No pygame dependency
• No external TTS API
• Fully local

Public API
----------
speak(text)
pause_speaking()
resume_speaking()
stop_speaking()
is_speaking()
is_paused()
get_tts_status()
self_test()
set_voice()
set_speech_rate()
clear_queue()

============================================================
"""

import os
import re
import signal
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_VOICE = os.getenv(
    "NOVA_VOICE",
    "Samantha"
)

DEFAULT_RATE = int(
    os.getenv(
        "NOVA_SPEECH_RATE",
        "180"
    )
)

MAX_TEXT_LENGTH = int(
    os.getenv(
        "NOVA_TTS_MAX_TEXT",
        "20000"
    )
)

MAX_SENTENCE_LENGTH = int(
    os.getenv(
        "NOVA_TTS_SENTENCE_LENGTH",
        "500"
    )
)

QUEUE_LIMIT = int(
    os.getenv(
        "NOVA_TTS_QUEUE_LIMIT",
        "50"
    )
)

CHUNK_DELAY = float(
    os.getenv(
        "NOVA_TTS_CHUNK_DELAY",
        "0.03"
    )
)


# ============================================================
# STATE
# ============================================================

@dataclass
class TTSState:

    speaking: bool = False

    paused: bool = False

    stopping: bool = False

    processing: bool = False

    queue_size: int = 0

    current_text: str = ""

    current_chunk: int = 0

    total_chunks: int = 0

    voice: str = DEFAULT_VOICE

    rate: int = DEFAULT_RATE

    last_error: Optional[str] = None


_state = TTSState()

_lock = threading.RLock()

_worker: Optional[threading.Thread] = None

_process: Optional[subprocess.Popen] = None

_queue = deque()

_shutdown_event = threading.Event()

_pause_event = threading.Event()

_stop_event = threading.Event()

_new_request_event = threading.Event()

_generation = 0

_state_callback: Optional[
    Callable[[dict], None]
] = None


# ============================================================
# PLATFORM
# ============================================================

def _is_macos() -> bool:

    return (
        os.uname().sysname
        == "Darwin"
    )


# ============================================================
# EXECUTABLE
# ============================================================

def _say_executable() -> str:

    candidates = [
        "/usr/bin/say",
        "/bin/say",
    ]

    for candidate in candidates:

        if os.path.exists(candidate):

            return candidate

    return "say"


# ============================================================
# STATE CALLBACK
# ============================================================

def set_state_callback(
    callback: Optional[
        Callable[[dict], None]
    ]
):

    global _state_callback

    with _lock:

        _state_callback = callback


def _emit_state():

    callback = None
    snapshot = None

    with _lock:

        callback = _state_callback

        snapshot = {
            "speaking": _state.speaking,
            "paused": _state.paused,
            "stopping": _state.stopping,
            "processing": _state.processing,
            "queue_size": len(_queue),
            "current_text": _state.current_text,
            "current_chunk": _state.current_chunk,
            "total_chunks": _state.total_chunks,
            "voice": _state.voice,
            "rate": _state.rate,
            "last_error": _state.last_error,
        }

    if callback:

        try:

            callback(snapshot)

        except Exception:

            pass


# ============================================================
# TEXT CLEANING
# ============================================================

def _clean_text(
    text: str
) -> str:

    text = str(
        text or ""
    )

    text = text.replace(
        "\x00",
        " "
    )

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL
        | re.IGNORECASE
    )

    text = re.sub(
        r"<thinking>.*?</thinking>",
        "",
        text,
        flags=re.DOTALL
        | re.IGNORECASE
    )

    # Remove common markdown artifacts.

    text = re.sub(
        r"```.*?```",
        "",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"`([^`]*)`",
        r"\1",
        text
    )

    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"\1",
        text
    )

    text = re.sub(
        r"\*(.*?)\*",
        r"\1",
        text
    )

    text = re.sub(
        r"__([^_]*)__",
        r"\1",
        text
    )

    # Normalize whitespace.

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# SENTENCE SPLITTER
# ============================================================

def _split_sentences(
    text: str
) -> list[str]:

    text = _clean_text(
        text
    )

    if not text:

        return []

    if len(text) <= MAX_SENTENCE_LENGTH:

        return [text]

    # Preserve sentence boundaries.

    pieces = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    chunks = []

    current = ""

    for piece in pieces:

        piece = piece.strip()

        if not piece:

            continue

        if not current:

            current = piece

        elif (
            len(current)
            + len(piece)
            + 1
            <= MAX_SENTENCE_LENGTH
        ):

            current += " " + piece

        else:

            chunks.append(
                current
            )

            current = piece

    if current:

        chunks.append(
            current
        )

    # Handle very long individual sentences.

    final = []

    for chunk in chunks:

        if len(chunk) <= MAX_SENTENCE_LENGTH:

            final.append(
                chunk
            )

            continue

        words = chunk.split()

        current = ""

        for word in words:

            if not current:

                current = word

            elif (
                len(current)
                + len(word)
                + 1
                <= MAX_SENTENCE_LENGTH
            ):

                current += " " + word

            else:

                final.append(
                    current
                )

                current = word

        if current:

            final.append(
                current
            )

    return final


# ============================================================
# PROCESS TERMINATION
# ============================================================

def _terminate_process(
    force: bool = False
):

    global _process

    process = None

    with _lock:

        process = _process

    if process is None:

        return

    try:

        if process.poll() is not None:

            return

        if force:

            process.kill()

        else:

            process.terminate()

        try:

            process.wait(
                timeout=1.0
            )

        except subprocess.TimeoutExpired:

            process.kill()

            try:

                process.wait(
                    timeout=1.0
                )

            except Exception:

                pass

    except Exception as error:

        with _lock:

            _state.last_error = str(
                error
            )


# ============================================================
# PAUSE PROCESS
# ============================================================

def _pause_process():

    process = None

    with _lock:

        process = _process

    if process is None:

        return False

    if process.poll() is not None:

        return False

    try:

        os.kill(
            process.pid,
            signal.SIGSTOP
        )

        return True

    except Exception as error:

        with _lock:

            _state.last_error = str(
                error
            )

        return False


# ============================================================
# RESUME PROCESS
# ============================================================

def _resume_process():

    process = None

    with _lock:

        process = _process

    if process is None:

        return False

    if process.poll() is not None:

        return False

    try:

        os.kill(
            process.pid,
            signal.SIGCONT
        )

        return True

    except Exception as error:

        with _lock:

            _state.last_error = str(
                error
            )

        return False


# ============================================================
# PLAY CHUNK
# ============================================================

def _play_chunk(
    text: str,
    generation: int,
    chunk_index: int,
    total_chunks: int
) -> bool:

    global _process

    if not text:

        return True

    with _lock:

        if generation != _generation:

            return False

        _state.current_text = text

        _state.current_chunk = (
            chunk_index
        )

        _state.total_chunks = (
            total_chunks
        )

        _state.processing = True

        _state.speaking = True

        _state.stopping = False

        _state.last_error = None

    _emit_state()

    command = [
        _say_executable(),
        "-v",
        _state.voice,
        "-r",
        str(_state.rate),
        text
    ]

    try:

        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )

    except Exception as error:

        with _lock:

            _state.last_error = str(
                error
            )

            _state.processing = False

        _emit_state()

        return False

    with _lock:

        if generation != _generation:

            try:

                process.terminate()

            except Exception:

                pass

            return False

        _process = process

    # --------------------------------------------------------
    # Monitor playback
    # --------------------------------------------------------

    while True:

        # ----------------------------------------------------
        # Generation changed
        # ----------------------------------------------------

        with _lock:

            current_generation = (
                _generation
            )

            stopping = (
                _stop_event.is_set()
            )

            paused = (
                _pause_event.is_set()
            )

        if generation != current_generation:

            _terminate_process(
                force=True
            )

            return False

        # ----------------------------------------------------
        # Stop requested
        # ----------------------------------------------------

        if stopping:

            _terminate_process(
                force=True
            )

            return False

        # ----------------------------------------------------
        # Pause requested
        # ----------------------------------------------------

        if paused:

            _pause_process()

            with _lock:

                _state.paused = True

                _state.speaking = True

                _state.processing = False

            _emit_state()

            # ------------------------------------------------
            # Wait while paused.
            #
            # Crucially, the `say` process is NOT restarted.
            # SIGSTOP freezes the exact audio-generation state.
            # ------------------------------------------------

            while _pause_event.is_set():

                if _stop_event.is_set():

                    _terminate_process(
                        force=True
                    )

                    return False

                with _lock:

                    if generation != _generation:

                        _terminate_process(
                            force=True
                        )

                        return False

                time.sleep(
                    0.05
                )

            # ------------------------------------------------
            # Resume the SAME process.
            # ------------------------------------------------

            _resume_process()

            with _lock:

                _state.paused = False

                _state.speaking = True

                _state.processing = True

            _emit_state()

        # ----------------------------------------------------
        # Check process
        # ----------------------------------------------------

        return_code = process.poll()

        if return_code is not None:

            stderr = ""

            try:

                if process.stderr:

                    stderr = (
                        process.stderr.read()
                        or ""
                    ).strip()

            except Exception:

                pass

            if return_code != 0:

                with _lock:

                    _state.last_error = (
                        stderr
                        or
                        f"`say` exited with code {return_code}"
                    )

                _emit_state()

                return False

            break

        time.sleep(
            0.03
        )

    with _lock:

        _process = None

        _state.processing = False

    _emit_state()

    return True


# ============================================================
# WORKER
# ============================================================

def _worker_loop(
    generation: int
):

    global _worker

    try:

        while not _shutdown_event.is_set():

            with _lock:

                if generation != _generation:

                    return

                if not _queue:

                    _state.speaking = False

                    _state.processing = False

                    _state.current_text = ""

                    _state.current_chunk = 0

                    _state.total_chunks = 0

                    _state.queue_size = 0

                    _state.stopping = False

                    _state.paused = False

                    _emit_state()

                    return

                item = _queue.popleft()

                _state.queue_size = len(
                    _queue
                )

            _emit_state()

            text = item

            chunks = _split_sentences(
                text
            )

            if not chunks:

                continue

            total = len(
                chunks
            )

            for index, chunk in enumerate(
                chunks,
                start=1
            ):

                with _lock:

                    if generation != _generation:

                        return

                success = _play_chunk(
                    chunk,
                    generation,
                    index,
                    total
                )

                if not success:

                    with _lock:

                        if generation != _generation:

                            return

                    break

                time.sleep(
                    CHUNK_DELAY
                )

    finally:

        with _lock:

            if generation == _generation:

                _state.speaking = False

                _state.processing = False

                _state.paused = False

                _state.stopping = False

                _state.current_text = ""

                _state.current_chunk = 0

                _state.total_chunks = 0

                _state.queue_size = len(
                    _queue
                )

                _process = None

            _worker = None

        _emit_state()


# ============================================================
# SPEAK
# ============================================================

def speak(
    text: str,
    interrupt: bool = True
) -> bool:

    global _generation
    global _worker

    text = _clean_text(
        text
    )

    if not text:

        return False

    if len(text) > MAX_TEXT_LENGTH:

        text = text[
            :MAX_TEXT_LENGTH
        ]

    with _lock:

        if interrupt:

            _generation += 1

            _stop_event.set()

            _pause_event.clear()

            _queue.clear()

            _terminate_process(
                force=True
            )

            _stop_event.clear()

        if len(_queue) >= QUEUE_LIMIT:

            _queue.popleft()

        _queue.append(
            text
        )

        _state.queue_size = len(
            _queue
        )

        _state.last_error = None

        generation = _generation

        if (
            _worker is None
            or not _worker.is_alive()
        ):

            _worker = threading.Thread(
                target=_worker_loop,
                args=(generation,),
                daemon=True,
                name="NOVA-TTS-Worker"
            )

            _worker.start()

    _emit_state()

    return True


# ============================================================
# PAUSE
# ============================================================

def pause_speaking() -> bool:

    with _lock:

        if not _state.speaking:

            return False

        if _state.paused:

            return True

        _pause_event.set()

    _emit_state()

    return True


# ============================================================
# RESUME
# ============================================================

def resume_speaking() -> bool:

    with _lock:

        if not _state.speaking:

            return False

        if not _state.paused:

            return True

        _pause_event.clear()

    _emit_state()

    return True


# ============================================================
# STOP
# ============================================================

def stop_speaking() -> bool:

    global _generation

    with _lock:

        _generation += 1

        _stop_event.set()

        _pause_event.clear()

        _queue.clear()

        _state.stopping = True

        _state.paused = False

        _state.processing = False

        _state.queue_size = 0

        _state.current_text = ""

        _state.current_chunk = 0

        _state.total_chunks = 0

    _terminate_process(
        force=True
    )

    with _lock:

        _state.speaking = False

        _state.stopping = False

        _state.stopping = False

        _stop_event.clear()

    _emit_state()

    return True


# ============================================================
# QUEUE
# ============================================================

def queue_speech(
    text: str
) -> bool:

    return speak(
        text,
        interrupt=False
    )


def clear_queue():

    with _lock:

        _queue.clear()

        _state.queue_size = 0

    _emit_state()


# ============================================================
# STATE
# ============================================================

def is_speaking() -> bool:

    with _lock:

        return bool(
            _state.speaking
        )


def is_paused() -> bool:

    with _lock:

        return bool(
            _state.paused
        )


def is_processing() -> bool:

    with _lock:

        return bool(
            _state.processing
        )


def get_tts_status() -> dict:

    with _lock:

        return {
            "success": True,
            "engine": "macOS say",
            "platform": "macOS",
            "voice": _state.voice,
            "rate": _state.rate,
            "speaking": _state.speaking,
            "paused": _state.paused,
            "processing": _state.processing,
            "stopping": _state.stopping,
            "queue_size": len(_queue),
            "current_text": _state.current_text,
            "current_chunk": _state.current_chunk,
            "total_chunks": _state.total_chunks,
            "last_error": _state.last_error,
        }


# ============================================================
# VOICE
# ============================================================

def set_voice(
    voice: str
) -> bool:

    voice = str(
        voice
    ).strip()

    if not voice:

        return False

    with _lock:

        _state.voice = voice

    _emit_state()

    return True


def get_voice() -> str:

    with _lock:

        return _state.voice


def list_voices() -> list[str]:

    if not _is_macos():

        return []

    try:

        result = subprocess.run(
            [
                _say_executable(),
                "-v",
                "?"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:

            return []

        voices = []

        for line in result.stdout.splitlines():

            line = line.strip()

            if not line:

                continue

            # macOS output format:
            #
            # Samantha            en_US
            #
            # Take the first field.

            parts = line.split()

            if parts:

                voices.append(
                    parts[0]
                )

        return voices

    except Exception:

        return []


# ============================================================
# SPEECH RATE
# ============================================================

def set_speech_rate(
    rate: int
) -> bool:

    try:

        rate = int(
            rate
        )

    except Exception:

        return False

    rate = max(
        80,
        min(
            400,
            rate
        )
    )

    with _lock:

        _state.rate = rate

    _emit_state()

    return True


def get_speech_rate() -> int:

    with _lock:

        return _state.rate


# ============================================================
# SELF TEST
# ============================================================

def self_test(
    speak_test: bool = False
) -> dict:

    result = {
        "success": False,
        "platform": os.uname().sysname,
        "engine": "macOS say",
        "say_available": False,
        "voice": get_voice(),
        "rate": get_speech_rate(),
        "voices_available": 0,
        "error": None,
    }

    if not _is_macos():

        result["error"] = (
            "NOVA TTS requires macOS."
        )

        return result

    say_path = _say_executable()

    try:

        check = subprocess.run(
            [
                say_path,
                "-v",
                get_voice(),
                ""
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        result["say_available"] = (
            check.returncode == 0
        )

    except Exception as error:

        result["error"] = str(
            error
        )

        return result

    voices = list_voices()

    result[
        "voices_available"
    ] = len(voices)

    if not result["say_available"]:

        result["error"] = (
            "macOS say command is unavailable "
            "or the selected voice is invalid."
        )

        return result

    if speak_test:

        try:

            speak(
                "NOVA speech test. "
                "Audio output is working.",
                interrupt=True
            )

        except Exception as error:

            result["error"] = str(
                error
            )

            return result

    result["success"] = True

    return result


# ============================================================
# SHUTDOWN
# ============================================================

def shutdown():

    global _generation

    with _lock:

        _generation += 1

        _shutdown_event.set()

        _stop_event.set()

        _pause_event.clear()

        _queue.clear()

    _terminate_process(
        force=True
    )

    with _lock:

        _state.speaking = False

        _state.paused = False

        _state.processing = False

        _state.stopping = False

        _state.queue_size = 0

    _emit_state()


# ============================================================
# CLEANUP ALIAS
# ============================================================

def cleanup():

    shutdown()


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 64)
    print("NOVA ADVANCED TEXT-TO-SPEECH")
    print("=" * 64)

    result = self_test()

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )

    if result["success"]:

        print()
        print(
            "Speaking test..."
        )

        speak(
            "Hello Saksham. "
            "This is NOVA. "
            "The advanced speech engine is working."
        )

        print(
            "Speech complete."
        )

    print()
    print("=" * 64)