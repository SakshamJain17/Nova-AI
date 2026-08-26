from __future__ import annotations

import math
import queue
import threading
import time
import tkinter as tk

import customtkinter as ctk


# ============================================================
# BACKEND
# ============================================================

try:
    from app.brain.model import ask_nova
except Exception as e:
    print(f"[MODEL ERROR] {e}")
    ask_nova = None


# Router is OPTIONAL.
# Your project currently does not have app.tools.router,
# so NOVA must not crash because of it.
try:
    from app.tools.router import route_command
except Exception:
    route_command = None
    print("[ROUTER] No router module found. AI mode enabled.")


try:
    from app.voice.speech_to_text import listen
except Exception as e:
    print(f"[STT ERROR] {e}")
    listen = None


# ============================================================
# TTS COMPATIBILITY
# ============================================================

try:
    from app.voice.text_to_speech import speak
except Exception as e:
    print(f"[TTS WARNING] speak unavailable: {e}")

    def speak(text):
        print(f"NOVA: {text}")


# Different TTS implementations may have different APIs.
try:
    from app.voice.text_to_speech import pause_speaking
except Exception:

    def pause_speaking():
        return False


try:
    from app.voice.text_to_speech import resume_speaking
except Exception:

    def resume_speaking():
        return False


try:
    from app.voice.text_to_speech import stop_speaking
except Exception:

    def stop_speaking():
        return False


try:
    from app.voice.text_to_speech import is_speaking
except Exception:

    def is_speaking():
        return False


try:
    from app.voice.text_to_speech import is_paused
except Exception:

    def is_paused():
        return False


# ============================================================
# OPTIONAL MEMORY
# ============================================================

try:
    from app.memory.memory import initialize_database
except Exception:

    def initialize_database():
        return None


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "NOVA"
USER_NAME = "Saksham"

WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 760

MIC_COOLDOWN = 1.5

STARTUP_DELAY = 800


# ============================================================
# COLORS
# ============================================================

BACKGROUND = "#05070B"
BLACK = "#000000"
SURFACE = "#090E15"

SURFACE_2 = "#0D141D"

SURFACE_3 = "#111C27"

BORDER = "#1B3042"

WHITE = "#F5F9FF"

TEXT = "#E7EEF7"

MUTED = "#7D91A5"

BLUE = "#159CFF"

BLUE_BRIGHT = "#38BDF8"

CYAN = "#00D9FF"

PURPLE = "#9B7BFF"

GREEN = "#2FE5A3"

YELLOW = "#FFD166"

RED = "#FF526D"


# ============================================================
# CUSTOMTKINTER
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


# ============================================================
# APPLICATION STATE
# ============================================================

class NovaState:

    def __init__(self):

        self.running = True

        self.listening = False

        self.processing = False

        self.speaking = False

        self.paused = False

        self.microphone_locked = False

        self.microphone_cooldown_until = 0.0

        self.voice_thread = None


state = NovaState()


# ============================================================
# UI QUEUE
# ============================================================

ui_queue = queue.Queue()


# ============================================================
# ORB
# ============================================================

orb_state = "idle"

orb_phase = 0.0


# ============================================================
# ROOT
# ============================================================

root = ctk.CTk()

root.title("NOVA — Personal AI")

root.geometry(
    f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
)

root.minsize(
    900,
    650
)

root.configure(
    fg_color=BACKGROUND
)

root.protocol(
    "WM_DELETE_WINDOW",
    lambda: shutdown()
)


# ============================================================
# ROOT GRID
# ============================================================

root.grid_columnconfigure(
    0,
    weight=1
)

root.grid_rowconfigure(
    1,
    weight=1
)


# ============================================================
# FUNCTION DEFINITIONS
# ============================================================
# IMPORTANT:
# All functions used by buttons are defined BEFORE the buttons.
# This prevents the NameError problems you encountered.
# ============================================================


def set_orb_state(new_state: str):

    global orb_state

    orb_state = new_state


def update_status(
    text: str,
    color: str
):

    try:

        status_label.configure(
            text=text
        )

        status_dot.configure(
            text_color=color
        )

    except Exception:
        pass


def add_message(
    speaker: str,
    text: str
):

    if not text:
        return

    try:

        timestamp = time.strftime(
            "%H:%M"
        )

        conversation.configure(
            state="normal"
        )

        tag = (
            "nova"
            if speaker == "NOVA"
            else "user"
        )

        conversation.insert(
            "end",
            f"{timestamp}  {speaker}\n",
            tag
        )

        conversation.insert(
            "end",
            f"{text}\n\n"
        )

        conversation.configure(
            state="disabled"
        )

        conversation.see(
            "end"
        )

    except Exception as e:

        print(
            f"[UI MESSAGE ERROR] {e}"
        )


# ============================================================
# MICROPHONE LOCK
# ============================================================

def lock_microphone():

    state.microphone_locked = True

    state.listening = False

    try:

        voice_button.configure(
            state="disabled"
        )

    except Exception:
        pass


def unlock_microphone():

    state.microphone_locked = False

    try:

        voice_button.configure(
            state="normal"
        )

    except Exception:
        pass


def unlock_microphone_after_cooldown():

    state.microphone_cooldown_until = (
        time.monotonic()
        + MIC_COOLDOWN
    )

    def check():

        if not state.running:
            return

        remaining = (
            state.microphone_cooldown_until
            - time.monotonic()
        )

        if remaining > 0:

            root.after(
                100,
                check
            )

            return

        if not state.speaking:

            unlock_microphone()

    root.after(
        100,
        check
    )


# ============================================================
# SPEECH
# ============================================================

def safe_speak(
    text: str
):

    if not text:
        return

    # --------------------------------------------------------
    # HARD MICROPHONE LOCK
    # --------------------------------------------------------

    lock_microphone()

    state.speaking = True

    state.paused = False

    set_orb_state(
        "speaking"
    )

    update_status(
        "SPEAKING",
        GREEN
    )

    try:

        speak(
            text
        )

    except Exception as e:

        print(
            f"[TTS ERROR] {e}"
        )

    finally:

        state.speaking = False

        state.paused = False

        set_orb_state(
            "idle"
        )

        update_status(
            "SYSTEM ONLINE",
            GREEN
        )

        unlock_microphone_after_cooldown()


# ============================================================
# PAUSE
# ============================================================

def pause_speech():

    if not state.speaking:

        status_message.configure(
            text="NOVA is not speaking."
        )

        return

    try:

        result = pause_speaking()

        state.paused = True

        set_orb_state(
            "paused"
        )

        update_status(
            "PAUSED",
            YELLOW
        )

        status_message.configure(
            text="Speech paused."
        )

        print(
            f"[TTS] Pause result: {result}"
        )

    except Exception as e:

        print(
            f"[TTS PAUSE ERROR] {e}"
        )

        status_message.configure(
            text="Pause is not supported by the current TTS engine."
        )


# ============================================================
# RESUME
# ============================================================

def resume_speech():

    if not state.speaking:

        status_message.configure(
            text="NOVA is not speaking."
        )

        return

    try:

        result = resume_speaking()

        state.paused = False

        set_orb_state(
            "speaking"
        )

        update_status(
            "SPEAKING",
            GREEN
        )

        status_message.configure(
            text="Speech resumed."
        )

        print(
            f"[TTS] Resume result: {result}"
        )

    except Exception as e:

        print(
            f"[TTS RESUME ERROR] {e}"
        )

        status_message.configure(
            text="Resume is not supported by the current TTS engine."
        )


# ============================================================
# STOP SPEECH
# ============================================================

def stop_speech():

    try:

        stop_speaking()

    except Exception as e:

        print(
            f"[TTS STOP ERROR] {e}"
        )

    state.speaking = False

    state.paused = False

    set_orb_state(
        "idle"
    )

    update_status(
        "SYSTEM ONLINE",
        GREEN
    )

    status_message.configure(
        text="Speech stopped."
    )

    lock_microphone()

    unlock_microphone_after_cooldown()


# ============================================================
# VOICE INPUT
# ============================================================

def start_voice():

    # --------------------------------------------------------
    # SAFETY CHECK 1
    # --------------------------------------------------------

    if state.speaking:

        status_message.configure(
            text="NOVA is speaking. Wait until it finishes."
        )

        return

    # --------------------------------------------------------
    # SAFETY CHECK 2
    # --------------------------------------------------------

    if state.microphone_locked:

        return

    # --------------------------------------------------------
    # SAFETY CHECK 3
    # --------------------------------------------------------

    if (
        time.monotonic()
        < state.microphone_cooldown_until
    ):

        return

    # --------------------------------------------------------
    # SAFETY CHECK 4
    # --------------------------------------------------------

    if state.listening:

        return

    # --------------------------------------------------------
    # SAFETY CHECK 5
    # --------------------------------------------------------

    if state.processing:

        status_message.configure(
            text="NOVA is still processing."
        )

        return

    # --------------------------------------------------------
    # STT AVAILABILITY
    # --------------------------------------------------------

    if listen is None:

        status_message.configure(
            text="Speech recognition is unavailable."
        )

        return

    # --------------------------------------------------------
    # START LISTENING
    # --------------------------------------------------------

    state.listening = True

    set_orb_state(
        "listening"
    )

    update_status(
        "LISTENING",
        CYAN
    )

    status_message.configure(
        text="Listening..."
    )

    try:

        voice_button.configure(
            state="disabled"
        )

    except Exception:
        pass

    state.voice_thread = threading.Thread(
        target=voice_worker,
        daemon=True
    )

    state.voice_thread.start()


# ============================================================
# VOICE WORKER
# ============================================================

def voice_worker():

    try:

        # FINAL microphone safety gate
        if (
            state.speaking
            or state.microphone_locked
        ):

            return

        result = listen()

        ui_queue.put(
            (
                "voice_result",
                result
            )
        )

    except Exception as e:

        ui_queue.put(
            (
                "error",
                f"Voice recognition error: {e}"
            )
        )

    finally:

        ui_queue.put(
            (
                "voice_finished",
                None
            )
        )


# ============================================================
# ROUTER
# ============================================================

def try_router(
    text: str
):

    if route_command is None:

        return None

    try:

        result = route_command(
            text
        )

    except TypeError:

        try:

            result = route_command(
                text,
                USER_NAME
            )

        except Exception as e:

            print(
                f"[ROUTER ERROR] {e}"
            )

            return None

    except Exception as e:

        print(
            f"[ROUTER ERROR] {e}"
        )

        return None

    if not isinstance(
        result,
        dict
    ):

        return None

    if not result.get(
        "handled",
        False
    ):

        return None

    return str(
        result.get(
            "message",
            result.get(
                "response",
                result.get(
                    "text",
                    "Done."
                )
            )
        )
    )


# ============================================================
# COMMAND PROCESSOR
# ============================================================

def process_command(
    text: str
):

    if not text:
        return

    if state.processing:

        status_message.configure(
            text="NOVA is still processing..."
        )

        return

    state.processing = True

    set_orb_state(
        "thinking"
    )

    update_status(
        "THINKING",
        PURPLE
    )

    status_message.configure(
        text="Thinking..."
    )

    threading.Thread(
        target=command_worker,
        args=(text,),
        daemon=True
    ).start()


# ============================================================
# COMMAND WORKER
# ============================================================

def command_worker(
    text: str
):

    try:

        cleaned = text.strip()

        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        if cleaned.lower() in {
            "exit",
            "quit",
            "goodbye",
            "shutdown nova",
            "stop nova"
        }:

            ui_queue.put(
                (
                    "shutdown",
                    None
                )
            )

            return

        # ----------------------------------------------------
        # ROUTER
        # ----------------------------------------------------

        routed = try_router(
            cleaned
        )

        if routed:

            ui_queue.put(
                (
                    "response",
                    routed
                )
            )

            return

        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        if ask_nova is None:

            raise RuntimeError(
                "NOVA model could not be loaded."
            )

        try:

            response = ask_nova(
                cleaned,
                USER_NAME
            )

        except TypeError:

            response = ask_nova(
                cleaned
            )

        if not response:

            response = (
                "I couldn't generate a response."
            )

        ui_queue.put(
            (
                "response",
                str(response).strip()
            )
        )

    except Exception as e:

        ui_queue.put(
            (
                "error",
                str(e)
            )
        )

    finally:

        ui_queue.put(
            (
                "processing_finished",
                None
            )
        )


# ============================================================
# HANDLE RESPONSE
# ============================================================

def handle_response(
    response: str
):

    if not response:
        return

    add_message(
        "NOVA",
        response
    )

    status_message.configure(
        text="Speaking..."
    )

    threading.Thread(
        target=safe_speak,
        args=(response,),
        daemon=True
    ).start()


# ============================================================
# ORB DRAWING
# ============================================================

def draw_orb():

    global orb_phase

    if not state.running:
        return

    try:

        orb_canvas.delete(
            "all"
        )

        width = max(
            orb_canvas.winfo_width(),
            400
        )

        height = max(
            orb_canvas.winfo_height(),
            400
        )

        cx = width / 2

        cy = height / 2 - 10

        if orb_state == "listening":

            primary = CYAN
            secondary = BLUE

            pulse = (
                1
                + 0.10
                * math.sin(
                    orb_phase * 2
                )
            )

        elif orb_state == "thinking":

            primary = PURPLE
            secondary = BLUE

            pulse = (
                1
                + 0.06
                * math.sin(
                    orb_phase * 3
                )
            )

        elif orb_state == "speaking":

            primary = GREEN
            secondary = CYAN

            pulse = (
                1
                + 0.09
                * math.sin(
                    orb_phase * 4
                )
            )

        elif orb_state == "paused":

            primary = YELLOW
            secondary = YELLOW

            pulse = 1.0

        elif orb_state == "error":

            primary = RED
            secondary = RED

            pulse = 1.0

        else:

            primary = BLUE
            secondary = CYAN

            pulse = (
                1
                + 0.025
                * math.sin(
                    orb_phase
                )
            )

        radius = (
            min(width, height)
            * 0.19
            * pulse
        )

        # ----------------------------------------------------
        # OUTER RINGS
        # ----------------------------------------------------

        for i in range(
            9,
            0,
            -1
        ):

            r = (
                radius
                + i * 12
            )

            orb_canvas.create_oval(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                outline=primary,
                width=1
            )

        # ----------------------------------------------------
        # MAIN ORB
        # ----------------------------------------------------

        orb_canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill=BLACK,
            outline=primary,
            width=4
        )

        # ----------------------------------------------------
        # INNER RING
        # ----------------------------------------------------

        inner = radius * 0.72

        orb_canvas.create_oval(
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
            outline=secondary,
            width=2
        )

        # ----------------------------------------------------
        # CORE
        # ----------------------------------------------------

        core = radius * 0.43

        orb_canvas.create_oval(
            cx - core,
            cy - core,
            cx + core,
            cy + core,
            fill=primary,
            outline=secondary,
            width=2
        )

        # ----------------------------------------------------
        # LOGO
        # ----------------------------------------------------

        orb_canvas.create_text(
            cx,
            cy,
            text="NOVA",
            fill=BLACK,
            font=(
                "Helvetica",
                18,
                "bold"
            )
        )

        # ----------------------------------------------------
        # STATE LABEL
        # ----------------------------------------------------

        state_text = {
            "idle": "READY",
            "listening": "LISTENING",
            "thinking": "THINKING",
            "speaking": "SPEAKING",
            "paused": "PAUSED",
            "error": "ERROR"
        }.get(
            orb_state,
            "READY"
        )

        orb_canvas.create_text(
            cx,
            cy + radius + 55,
            text=state_text,
            fill=MUTED,
            font=(
                "Helvetica",
                10,
                "bold"
            )
        )

        orb_phase += 0.08

    except Exception as e:

        print(
            f"[ORB ERROR] {e}"
        )

    root.after(
        35,
        draw_orb
    )


# ============================================================
# BUILD UI
# ============================================================

header = ctk.CTkFrame(
    root,
    fg_color=BACKGROUND,
    corner_radius=0
)

header.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=30,
    pady=(22, 0)
)

header.grid_columnconfigure(
    1,
    weight=1
)


brand = ctk.CTkLabel(
    header,
    text="NOVA",
    text_color=WHITE,
    font=(
        "Helvetica",
        27,
        "bold"
    )
)

brand.grid(
    row=0,
    column=0,
    sticky="w"
)


subtitle = ctk.CTkLabel(
    header,
    text="PERSONAL AI",
    text_color=MUTED,
    font=(
        "Helvetica",
        10,
        "bold"
    )
)

subtitle.grid(
    row=0,
    column=1,
    sticky="w",
    padx=15,
    pady=(7, 0)
)


status_container = ctk.CTkFrame(
    header,
    fg_color=SURFACE,
    corner_radius=20
)

status_container.grid(
    row=0,
    column=2,
    sticky="e"
)


status_dot = ctk.CTkLabel(
    status_container,
    text="●",
    text_color=GREEN,
    font=(
        "Helvetica",
        12,
        "bold"
    )
)

status_dot.pack(
    side="left",
    padx=(10, 4)
)


status_label = ctk.CTkLabel(
    status_container,
    text="SYSTEM ONLINE",
    text_color=TEXT,
    font=(
        "Helvetica",
        9,
        "bold"
    )
)

status_label.pack(
    side="left",
    padx=(0, 12),
    pady=7
)


# ============================================================
# MAIN CONTENT
# ============================================================

main = ctk.CTkFrame(
    root,
    fg_color=BACKGROUND,
    corner_radius=0
)

main.grid(
    row=1,
    column=0,
    sticky="nsew",
    padx=30,
    pady=18
)

main.grid_columnconfigure(
    0,
    weight=3
)

main.grid_columnconfigure(
    1,
    weight=2
)

main.grid_rowconfigure(
    0,
    weight=1
)


# ============================================================
# ORB PANEL
# ============================================================

orb_panel = ctk.CTkFrame(
    main,
    fg_color=SURFACE,
    corner_radius=30,
    border_width=1,
    border_color=BORDER
)

orb_panel.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=(0, 9)
)

orb_panel.grid_rowconfigure(
    0,
    weight=1
)

orb_panel.grid_columnconfigure(
    0,
    weight=1
)


orb_canvas = tk.Canvas(
    orb_panel,
    background=SURFACE,
    highlightthickness=0,
    borderwidth=0
)

orb_canvas.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=10,
    pady=10
)


orb_hint = ctk.CTkLabel(
    orb_panel,
    text="Click the orb to speak",
    text_color=MUTED,
    font=(
        "Helvetica",
        11
    )
)

orb_hint.grid(
    row=1,
    column=0,
    pady=(0, 20)
)


# ============================================================
# CONVERSATION PANEL
# ============================================================

conversation_panel = ctk.CTkFrame(
    main,
    fg_color=SURFACE,
    corner_radius=30,
    border_width=1,
    border_color=BORDER
)

conversation_panel.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=(9, 0)
)


conversation_title = ctk.CTkLabel(
    conversation_panel,
    text="CONVERSATION",
    text_color=TEXT,
    font=(
        "Helvetica",
        12,
        "bold"
    )
)

conversation_title.pack(
    anchor="w",
    padx=20,
    pady=(20, 10)
)


conversation = ctk.CTkTextbox(
    conversation_panel,
    fg_color=SURFACE_2,
    text_color=TEXT,
    corner_radius=18,
    border_width=0,
    font=(
        "Helvetica",
        11
    ),
    wrap="word"
)

conversation.pack(
    fill="both",
    expand=True,
    padx=15,
    pady=(0, 15)
)

conversation.configure(
    state="disabled"
)

conversation.tag_config(
    "nova",
    foreground=GREEN
)

conversation.tag_config(
    "user",
    foreground=BLUE_BRIGHT
)


# ============================================================
# BOTTOM
# ============================================================

bottom = ctk.CTkFrame(
    root,
    fg_color=BACKGROUND,
    corner_radius=0
)

bottom.grid(
    row=2,
    column=0,
    sticky="ew",
    padx=30,
    pady=(0, 22)
)

bottom.grid_columnconfigure(
    0,
    weight=1
)


# ============================================================
# INPUT CONTAINER
# ============================================================

input_container = ctk.CTkFrame(
    bottom,
    fg_color=SURFACE,
    corner_radius=22,
    border_width=1,
    border_color=BORDER
)

input_container.grid(
    row=0,
    column=0,
    sticky="ew"
)

input_container.grid_columnconfigure(
    0,
    weight=1
)


entry = ctk.CTkEntry(
    input_container,
    placeholder_text="Ask NOVA anything...",
    placeholder_text_color=MUTED,
    text_color=WHITE,
    fg_color=SURFACE,
    border_width=0,
    font=(
        "Helvetica",
        13
    ),
    height=48
)

entry.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=(18, 5),
    pady=7
)


# ============================================================
# BUTTON FACTORY
# ============================================================

def make_button(
    parent,
    text,
    command,
    fg=SURFACE_3,
    hover=BORDER,
    text_color=TEXT
):

    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=fg,
        hover_color=hover,
        text_color=text_color,
        corner_radius=15,
        height=38,
        font=(
            "Helvetica",
            10,
            "bold"
        )
    )


# ============================================================
# SEND COMMAND
# ============================================================

def send_command():

    text = entry.get().strip()

    if not text:
        return

    entry.delete(
        0,
        "end"
    )

    add_message(
        "YOU",
        text
    )

    process_command(
        text
    )


# ============================================================
# BUTTONS
# ============================================================

voice_button = make_button(
    input_container,
    "🎤",
    start_voice,
    SURFACE_3,
    BORDER,
    TEXT
)

voice_button.grid(
    row=0,
    column=1,
    padx=4,
    pady=7
)


send_button = make_button(
    input_container,
    "SEND",
    send_command,
    BLUE,
    CYAN,
    BLACK
)

send_button.grid(
    row=0,
    column=2,
    padx=(4, 7),
    pady=7
)


# ============================================================
# SPEECH CONTROL BUTTONS
# ============================================================

controls = ctk.CTkFrame(
    bottom,
    fg_color=BACKGROUND
)

controls.grid(
    row=1,
    column=0,
    pady=(9, 0)
)


pause_button = make_button(
    controls,
    "PAUSE",
    pause_speech
)

pause_button.pack(
    side="left",
    padx=4
)


resume_button = make_button(
    controls,
    "RESUME",
    resume_speech
)

resume_button.pack(
    side="left",
    padx=4
)


stop_button = make_button(
    controls,
    "STOP",
    stop_speech,
    SURFACE_3,
    RED
)

stop_button.pack(
    side="left",
    padx=4
)
def shutdown():
    """Safely close NOVA."""
    try:
        runtime.active = False
    except Exception:
        pass

    try:
        root.destroy()
    except Exception:
        try:
            app.destroy()
        except Exception:
            pass
        
exit_button = make_button(
    controls,
    "EXIT",
    shutdown,   
    SURFACE_3,
    RED,
    RED
)

exit_button.pack(
    side="left",
    padx=4
)

# ============================================================
# STATUS MESSAGE
# ============================================================

status_message = ctk.CTkLabel(
    bottom,
    text="How can I help you, Saksham?",
    text_color=MUTED,
    font=(
        "Helvetica",
        10
    )
)

status_message.grid(
    row=2,
    column=0,
    pady=(7, 0)
)


# ============================================================
# KEYBOARD
# ============================================================

entry.bind(
    "<Return>",
    lambda event: send_command()
)


# ============================================================
# ORB CLICK
# ============================================================

orb_canvas.bind(
    "<Button-1>",
    lambda event: start_voice()
)


# ============================================================
# STARTUP GREETING
# ============================================================

def startup_greeting():

    if not state.running:
        return

    greeting = (
        "Hello Saksham. NOVA is ready. "
        "How can I assist you?"
    )

    add_message(
        "NOVA",
        greeting
    )

    status_message.configure(
        text="How can I help you, Saksham?"
    )

    threading.Thread(
        target=safe_speak,
        args=(greeting,),
        daemon=True
    ).start()


# ============================================================
# UI QUEUE PROCESSOR
# ============================================================

def process_ui_queue():

    if not state.running:
        return

    try:

        while True:

            event, data = (
                ui_queue.get_nowait()
            )

            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            if event == "response":

                state.processing = False

                handle_response(
                    data
                )

            # ------------------------------------------------
            # VOICE RESULT
            # ------------------------------------------------

            elif event == "voice_result":

                # NEVER process microphone audio if NOVA
                # has started speaking.
                if state.speaking:
                    continue

                if data:

                    text = str(
                        data
                    ).strip()

                    if text:

                        add_message(
                            "YOU",
                            text
                        )

                        process_command(
                            text
                        )

            # ------------------------------------------------
            # VOICE FINISHED
            # ------------------------------------------------

            elif event == "voice_finished":

                state.listening = False

                if not state.speaking:

                    set_orb_state(
                        "idle"
                    )

                    update_status(
                        "SYSTEM ONLINE",
                        GREEN
                    )

                if not state.microphone_locked:

                    try:

                        voice_button.configure(
                            state="normal"
                        )

                    except Exception:
                        pass

            # ------------------------------------------------
            # PROCESSING FINISHED
            # ------------------------------------------------

            elif event == "processing_finished":

                state.processing = False

            # ------------------------------------------------
            # ERROR
            # ------------------------------------------------

            elif event == "error":

                state.processing = False

                set_orb_state(
                    "error"
                )

                update_status(
                    "ERROR",
                    RED
                )

                status_message.configure(
                    text=str(data)
                )

                add_message(
                    "SYSTEM",
                    str(data)
                )

                root.after(
                    1800,
                    lambda: (
                        set_orb_state("idle"),
                        update_status(
                            "SYSTEM ONLINE",
                            GREEN
                        )
                    )
                )

            # ------------------------------------------------
            # SHUTDOWN
            # ------------------------------------------------

            elif event == "shutdown":

                shutdown()

    except queue.Empty:
        pass

    # ========================================================
    # SYNCHRONIZE TTS STATE
    # ========================================================

    try:

        currently_speaking = bool(
            is_speaking()
        )

        currently_paused = bool(
            is_paused()
        )

        if currently_paused:

            state.speaking = True

            state.paused = True

            state.microphone_locked = True

            set_orb_state(
                "paused"
            )

            update_status(
                "PAUSED",
                YELLOW
            )

        elif currently_speaking:

            state.speaking = True

            state.paused = False

            # HARD LOCK
            state.microphone_locked = True

            try:

                voice_button.configure(
                    state="disabled"
                )

            except Exception:
                pass

            set_orb_state(
                "speaking"
            )

            update_status(
                "SPEAKING",
                GREEN
            )

        elif (
            state.speaking
            and not currently_speaking
        ):

            state.speaking = False

            state.paused = False

            set_orb_state(
                "idle"
            )

            update_status(
                "SYSTEM ONLINE",
                GREEN
            )

            unlock_microphone_after_cooldown()

        elif (
            not state.listening
            and not state.processing
            and not state.speaking
        ):

            set_orb_state(
                "idle"
            )

            update_status(
                "SYSTEM ONLINE",
                GREEN
            )

    except Exception:
        pass

    root.after(
        100,
        process_ui_queue
    )


# ============================================================
# SHUTDOWN
# ============================================================

def shutdown():

    if not state.running:
        return

    state.running = False

    try:

        stop_speaking()

    except Exception:
        pass

    try:

        root.destroy()

    except Exception:
        pass


# ============================================================
# MEMORY INITIALIZATION
# ============================================================

try:

    initialize_database()

except Exception as e:

    print(
        f"[MEMORY WARNING] {e}"
    )


# ============================================================
# INITIAL UI
# ============================================================

entry.focus_set()

draw_orb()

root.after(
    100,
    process_ui_queue
)

root.after(
    STARTUP_DELAY,
    startup_greeting
)


# ============================================================
# RUN
# ============================================================

root.mainloop()