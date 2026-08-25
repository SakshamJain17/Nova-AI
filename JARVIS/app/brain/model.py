from __future__ import annotations

"""
============================================================
NOVA — ADVANCED LOCAL AI MODEL
============================================================

Purpose
-------
Local reasoning and conversation engine for NOVA.

Primary backend
---------------
Ollama + Qwen3:8b

Features
--------
• Local Ollama inference
• Persistent conversation history
• Current-session conversation memory
• Cross-session conversation memory
• Follow-up context
• Previous-command context
• Canonical Saksham identity
• Profile integration
• Existing memory integration
• Conscience integration
• Qwen thinking-block cleanup
• Duplicate-response protection
• Context-window management
• Retry/recovery
• Model health checks
• Runtime statistics
• Diagnostics
• Self-test
• General-purpose AI behavior
• Tool-router compatible architecture
• No direct arbitrary system execution

Computer actions MUST continue to be handled by:
    app.brain.tool_router

============================================================
"""

import json
import logging
import os
import re
import time

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Optional

import ollama


# ============================================================
# CONFIGURATION
# ============================================================

NOVA_NAME = "NOVA"

CANONICAL_USER_NAME = "Saksham"

MODEL_NAME = os.getenv(
    "NOVA_MODEL",
    "qwen3:8b",
)

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "",
).strip()


# ------------------------------------------------------------
# Conversation settings
# ------------------------------------------------------------

MAX_HISTORY_MESSAGES = int(
    os.getenv(
        "NOVA_MAX_HISTORY",
        "30",
    )
)

MAX_CONTEXT_CHARS = int(
    os.getenv(
        "NOVA_MAX_CONTEXT",
        "18000",
    )
)

MAX_RESPONSE_CHARS = int(
    os.getenv(
        "NOVA_MAX_RESPONSE",
        "12000",
    )
)

MAX_PERSISTED_MESSAGES = int(
    os.getenv(
        "NOVA_PERSISTED_MESSAGES",
        "100",
    )
)


# ------------------------------------------------------------
# Ollama generation settings
# ------------------------------------------------------------

TEMPERATURE = float(
    os.getenv(
        "NOVA_TEMPERATURE",
        "0.35",
    )
)

TOP_P = float(
    os.getenv(
        "NOVA_TOP_P",
        "0.90",
    )
)

REPEAT_PENALTY = float(
    os.getenv(
        "NOVA_REPEAT_PENALTY",
        "1.12",
    )
)

NUM_CTX = int(
    os.getenv(
        "NOVA_NUM_CTX",
        "8192",
    )
)

MAX_RETRIES = int(
    os.getenv(
        "NOVA_MAX_RETRIES",
        "2",
    )
)


# ============================================================
# STORAGE
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]

DATA_DIRECTORY = (
    PROJECT_ROOT / "data"
)

CONVERSATION_FILE = (
    DATA_DIRECTORY / "nova_conversation.json"
)


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(
    "NOVA.Model"
)

if not logger.handlers:

    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "[NOVA MODEL %(levelname)s] %(message)s"
    )

    handler.setFormatter(
        formatter
    )

    logger.addHandler(
        handler
    )

logger.setLevel(
    logging.INFO
)


# ============================================================
# OPTIONAL PROFILE INTEGRATION
# ============================================================

try:

    from app.memory.profile import (
        get_user_name,
        get_profile_context,
    )

except Exception as error:

    logger.warning(
        "Profile integration unavailable: %s",
        error,
    )

    def get_user_name() -> str:
        return CANONICAL_USER_NAME

    def get_profile_context() -> str:
        return (
            "Canonical user name: Saksham"
        )


# ============================================================
# OPTIONAL CONSCIENCE INTEGRATION
# ============================================================

try:

    from app.brain.conscience import (
        build_personal_context,
    )

except Exception as error:

    logger.warning(
        "Conscience integration unavailable: %s",
        error,
    )

    def build_personal_context() -> str:
        return ""


# ============================================================
# OPTIONAL MEMORY INTEGRATION
# ============================================================

try:

    from app.memory.memory import (
        get_all_memories,
    )

except Exception as error:

    logger.warning(
        "Memory integration unavailable: %s",
        error,
    )

    def get_all_memories() -> list[Any]:
        return []


# ============================================================
# GLOBAL STATE
# ============================================================

_lock = RLock()

_history: deque[dict[str, str]] = deque(
    maxlen=MAX_HISTORY_MESSAGES
)

_persisted_history: list[
    dict[str, str]
] = []

_last_response = ""

_last_user_input = ""

_last_error: Optional[str] = None

_last_request_time = 0.0

_last_response_time = 0.0

_total_requests = 0

_successful_requests = 0

_failed_requests = 0

_retry_count = 0

_model_available = False

_initialized = False


# ============================================================
# RUNTIME STATE
# ============================================================

@dataclass
class RuntimeState:

    active: bool = True

    thinking: bool = False

    speaking: bool = False

    listening: bool = False

    executing_tool: bool = False

    interrupted: bool = False


runtime = RuntimeState()


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are NOVA, Saksham's advanced personal AI assistant.

You run locally on Saksham's computer using a local language
model.

============================================================
IDENTITY
============================================================

Your name is NOVA.

Your primary user is:

Saksham

The canonical spelling is ALWAYS:

Saksham

Never change his name to:

Saxham
Saxam
Sakshm
Thaksam
Thaxam
Sakshum

Speech recognition mistakes do not change the user's identity.

Saksham may sometimes be called "Boss".

Do not call him Boss in every response.

============================================================
GENERAL PURPOSE
============================================================

You are NOT a work-only assistant.

You are a GENERAL-PURPOSE personal AI.

You can discuss reasonable topics including:

• Sports
• Cricket
• Football
• Tennis
• Snooker
• Billiards
• Basketball
• Formula 1
• Athletes
• Sportspeople
• Actors
• Musicians
• Movies
• Books
• Science
• Mathematics
• History
• Geography
• Technology
• Artificial intelligence
• Programming
• Computer science
• School subjects
• Business
• Productivity
• Gaming
• Entertainment
• General knowledge
• Casual conversation
• Saksham's projects
• Saksham's computer

Never reject a question merely because it is unrelated to
Saksham's work.

BAD:
"That isn't relevant to your work."

BAD:
"I only help with your projects."

GOOD:
"Sure. Here's what I know..."

============================================================
CURRENT INFORMATION
============================================================

You are a local AI.

Do not pretend to have live internet information.

For stable questions, answer using your knowledge.

For questions requiring current information such as:

• today's sports results
• current scores
• today's news
• current prices
• recent events
• current schedules
• live statistics
• current weather

do not fabricate information.

If an external search tool is available, the tool layer should
handle the search.

If no search capability exists, clearly say that current
information cannot be verified.

============================================================
CONVERSATION
============================================================

Use the conversation history supplied to you.

Understand follow-up references.

Example:

User:
"Who is Cristiano Ronaldo?"

NOVA:
" Cristiano Ronaldo is..."

User:
"How old is he?"

Interpret "he" as Cristiano Ronaldo.

User:
"What club does he play for?"

Use the previous context.

Do not unnecessarily ask the user to repeat information that
already exists in the conversation.

============================================================
FOLLOW-UP LANGUAGE
============================================================

Understand phrases such as:

"he"
"she"
"it"
"that"
"this"
"the previous one"
"the last one"
"again"
"repeat"
"repeat that"
"repeat my command"
"do that again"
"open it"
"close it"
"tell me more"
"explain that"
"why?"
"how?"
"what about him?"
"what about her?"

Use context when the reference is clear.

============================================================
COMPUTER ACTIONS
============================================================

Actual computer operations are handled by the tool layer.

Never claim that an application was opened unless the tool
layer reports success.

Never claim that a file was created unless the tool layer
reports success.

Never claim that a message was sent unless the tool layer
reports success.

Never execute arbitrary shell commands merely because the
language model generated them.

The approved tool/router layer handles computer actions.

============================================================
PERSONALITY
============================================================

Be:

• Intelligent
• Calm
• Natural
• Helpful
• Direct
• Context-aware
• Honest
• Technically capable

Avoid repetitive greetings.

Do not repeatedly say:

"Hello Saksham."

Do not repeatedly say:

"NOVA is ready."

Do not repeatedly say:

"How can I assist you?"

Do not repeat the user's complete sentence unnecessarily.

============================================================
RESPONSE STYLE
============================================================

Simple question:
Give a concise answer.

Complex question:
Give a structured explanation.

Technical question:
Be precise.

Casual conversation:
Be natural.

Computer action:
Keep the response short after successful execution.

Example:

"Calculator is open."

Do not produce a long explanation for a simple action.

============================================================
NO FABRICATION
============================================================

Never pretend an action happened.

Never pretend to have access to something that does not exist.

Never fabricate current information.

Never fabricate personal memories.

Never invent computer results.

============================================================
PRIVACY
============================================================

Treat Saksham's personal information as private.

Use stored information only when it is relevant.

Do not expose internal implementation details unless asked.

============================================================
LOCAL-FIRST
============================================================

Prefer local processing.

The primary model is Qwen through Ollama.

Do not claim cloud access unless configured.

============================================================
FINAL RULE
============================================================

Answer Saksham's actual request.

NOVA is a general-purpose personal AI.

A question does not need to be related to Saksham's work.
"""


# ============================================================
# CLIENT
# ============================================================

def _client() -> ollama.Client:

    if OLLAMA_HOST:

        return ollama.Client(
            host=OLLAMA_HOST
        )

    return ollama.Client()


# ============================================================
# INITIALIZATION
# ============================================================

def initialize_model() -> bool:

    global _initialized

    with _lock:

        if _initialized:

            return True

        try:

            DATA_DIRECTORY.mkdir(
                parents=True,
                exist_ok=True,
            )

        except Exception as error:

            logger.warning(
                "Could not create data directory: %s",
                error,
            )

        _load_persistent_history()

        _initialized = True

        return True


# ============================================================
# IDENTITY
# ============================================================

def canonical_user_name() -> str:

    return CANONICAL_USER_NAME


def assistant_name() -> str:

    return NOVA_NAME


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(text).strip().lower(),
    )


# ============================================================
# NAME PROTECTION
# ============================================================

def _protect_name(
    text: str,
) -> str:

    if not text:

        return ""

    replacements = {
        r"\bsaxham\b": "Saksham",
        r"\bsaxam\b": "Saksham",
        r"\bsakshm\b": "Saksham",
        r"\bthaksam\b": "Saksham",
        r"\bthaxam\b": "Saksham",
        r"\bsakshum\b": "Saksham",
        r"\bsakshyam\b": "Saksham",
    }

    for pattern, replacement in replacements.items():

        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE,
        )

    return text


# ============================================================
# THINKING CLEANUP
# ============================================================

def _remove_thinking(
    text: str,
) -> str:

    if not text:

        return ""

    patterns = [
        r"<think>.*?</think>",
        r"<thinking>.*?</thinking>",
        r"<\|think\|>.*?<\|end\|>",
    ]

    for pattern in patterns:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

    return text.strip()


# ============================================================
# RESPONSE CLEANUP
# ============================================================

def clean_response(
    response: str,
) -> str:

    if not response:

        return ""

    response = str(
        response
    )

    response = _remove_thinking(
        response
    )

    response = re.sub(
        r"^\s*(assistant|nova)\s*:\s*",
        "",
        response,
        flags=re.IGNORECASE,
    )

    artifacts = [
        "<|assistant|>",
        "<|user|>",
        "<|system|>",
        "<|endoftext|>",
        "<|im_start|>",
        "<|im_end|>",
    ]

    for artifact in artifacts:

        response = response.replace(
            artifact,
            "",
        )

    response = _protect_name(
        response
    )

    response = response.strip()

    if len(response) > MAX_RESPONSE_CHARS:

        response = (
            response[
                :MAX_RESPONSE_CHARS
            ]
            .rstrip()
        )

        response += "..."

    return response


# ============================================================
# MODEL CHECK
# ============================================================

def check_model() -> dict[str, Any]:

    global _model_available
    global _last_error

    try:

        client = _client()

        result = client.list()

        models: list[str] = []

        raw_models = getattr(
            result,
            "models",
            [],
        )

        for model in raw_models:

            name = getattr(
                model,
                "model",
                None,
            )

            if name:

                models.append(
                    str(name)
                )

        available = any(
            name == MODEL_NAME
            or name.startswith(
                MODEL_NAME + ":"
            )
            for name in models
        )

        _model_available = available

        if available:

            _last_error = None

        else:

            _last_error = (
                f"Model '{MODEL_NAME}' "
                "is not installed."
            )

        return {
            "success": True,
            "ollama": True,
            "model": MODEL_NAME,
            "model_available": available,
            "available_models": models,
        }

    except Exception as error:

        _model_available = False

        _last_error = str(
            error
        )

        return {
            "success": False,
            "ollama": False,
            "model": MODEL_NAME,
            "model_available": False,
            "available_models": [],
            "error": str(error),
        }


# ============================================================
# PROFILE CONTEXT
# ============================================================

def _profile_context() -> str:

    try:

        context = get_profile_context()

        if context:

            return str(
                context
            ).strip()

    except Exception as error:

        logger.warning(
            "Profile context failed: %s",
            error,
        )

    return (
        "Canonical user name: Saksham"
    )


# ============================================================
# MEMORY CONTEXT
# ============================================================

def _memory_context() -> str:

    try:

        memories = get_all_memories()

        if not memories:

            return ""

        lines: list[str] = []

        for memory in memories:

            if isinstance(
                memory,
                dict,
            ):

                key = (
                    memory.get("key")
                    or memory.get("name")
                    or memory.get("type")
                    or "memory"
                )

                value = (
                    memory.get("value")
                    or memory.get("content")
                    or memory.get("memory")
                    or ""
                )

                if value:

                    lines.append(
                        f"- {key}: {value}"
                    )

            elif isinstance(
                memory,
                str,
            ):

                lines.append(
                    f"- {memory}"
                )

        if not lines:

            return ""

        return (
            "KNOWN MEMORIES:\n"
            + "\n".join(lines)
        )

    except Exception as error:

        logger.warning(
            "Memory context unavailable: %s",
            error,
        )

        return ""


# ============================================================
# CONSCIENCE CONTEXT
# ============================================================

def _conscience_context() -> str:

    try:

        context = (
            build_personal_context()
        )

        if context:

            return str(
                context
            ).strip()

    except Exception as error:

        logger.warning(
            "Conscience context unavailable: %s",
            error,
        )

    return ""


# ============================================================
# CONTEXT BUILDER
# ============================================================

def build_context() -> str:

    sections: list[str] = []

    profile = _profile_context()

    if profile:

        sections.append(
            "PROFILE:\n"
            + profile
        )

    conscience = (
        _conscience_context()
    )

    if conscience:

        sections.append(
            "PERSONAL CONTEXT:\n"
            + conscience
        )

    memory = _memory_context()

    if memory:

        sections.append(
            memory
        )

    combined = "\n\n".join(
        sections
    )

    if len(combined) > MAX_CONTEXT_CHARS:

        combined = combined[
            -MAX_CONTEXT_CHARS:
        ]

    return combined


# ============================================================
# PERSISTENT HISTORY
# ============================================================

def _load_persistent_history() -> None:

    global _persisted_history

    try:

        if not CONVERSATION_FILE.exists():

            _persisted_history = []

            return

        with CONVERSATION_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

        if not isinstance(
            data,
            list,
        ):

            _persisted_history = []

            return

        cleaned: list[
            dict[str, str]
        ] = []

        for item in data:

            if not isinstance(
                item,
                dict,
            ):

                continue

            role = item.get(
                "role"
            )

            content = item.get(
                "content"
            )

            if role not in {
                "user",
                "assistant",
            }:

                continue

            if not content:

                continue

            cleaned.append(
                {
                    "role": str(role),
                    "content": str(content),
                }
            )

        _persisted_history = cleaned[
            -MAX_PERSISTED_MESSAGES:
        ]

        # Restore only the most recent messages into the
        # active context window.
        _history.clear()

        for item in _persisted_history[
            -MAX_HISTORY_MESSAGES:
        ]:

            _history.append(
                item
            )

        logger.info(
            "Loaded %d persistent messages.",
            len(_persisted_history),
        )

    except Exception as error:

        logger.warning(
            "Could not load conversation memory: %s",
            error,
        )

        _persisted_history = []


def _save_persistent_history() -> None:

    try:

        DATA_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = _persisted_history[
            -MAX_PERSISTED_MESSAGES:
        ]

        temporary_file = (
            CONVERSATION_FILE.with_suffix(
                ".tmp"
            )
        )

        with temporary_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        temporary_file.replace(
            CONVERSATION_FILE
        )

    except Exception as error:

        logger.warning(
            "Could not save conversation memory: %s",
            error,
        )


# ============================================================
# HISTORY
# ============================================================

def _add_history(
    role: str,
    content: str,
) -> None:

    if not content:

        return

    item = {
        "role": role,
        "content": str(content),
    }

    with _lock:

        _history.append(
            item
        )

        _persisted_history.append(
            item
        )

        if len(
            _persisted_history
        ) > MAX_PERSISTED_MESSAGES:

            del _persisted_history[
                :-MAX_PERSISTED_MESSAGES
            ]

        _save_persistent_history()


def get_history() -> list[dict[str, str]]:

    initialize_model()

    with _lock:

        return list(
            _history
        )


def get_persistent_history() -> list[
    dict[str, str]
]:

    initialize_model()

    with _lock:

        return list(
            _persisted_history
        )


def clear_history(
    clear_persistent: bool = False,
) -> None:

    with _lock:

        _history.clear()

        if clear_persistent:

            _persisted_history.clear()

            _save_persistent_history()


def reset_conversation() -> None:

    clear_history(
        clear_persistent=False
    )


# ============================================================
# LAST MESSAGE HELPERS
# ============================================================

def get_last_user_input() -> str:

    return _last_user_input


def get_last_response() -> str:

    return _last_response


def get_previous_turn() -> dict[str, str]:

    with _lock:

        user_message = ""

        assistant_message = ""

        for item in reversed(
            _history
        ):

            if (
                not assistant_message
                and item["role"] == "assistant"
            ):

                assistant_message = (
                    item["content"]
                )

            elif (
                not user_message
                and item["role"] == "user"
            ):

                user_message = (
                    item["content"]
                )

            if (
                user_message
                and assistant_message
            ):

                break

        return {
            "user": user_message,
            "assistant": assistant_message,
        }


# ============================================================
# INTENT CLASSIFICATION
# ============================================================

def classify_intent(
    user_input: str,
) -> str:

    text = _normalize(
        user_input
    )

    if not text:

        return "empty"

    if text in {
        "exit",
        "quit",
        "goodbye",
        "shutdown nova",
        "stop nova",
        "close nova",
    }:

        return "shutdown"

    action_starts = (
        "open ",
        "launch ",
        "start ",
        "close ",
        "quit ",
        "stop ",
        "play ",
        "pause ",
        "send ",
        "create ",
        "delete ",
        "lock ",
        "unlock ",
        "search ",
        "go to ",
        "visit ",
        "turn on ",
        "turn off ",
        "take ",
    )

    if text.startswith(
        action_starts
    ):

        return "action"

    follow_up_terms = {
        "again",
        "repeat",
        "repeat that",
        "repeat command",
        "repeat my command",
        "do that again",
        "do it again",
        "open it",
        "close it",
        "what about him",
        "what about her",
        "what about it",
        "tell me more",
        "explain that",
    }

    if text in follow_up_terms:

        return "follow_up"

    question_starts = (
        "what ",
        "why ",
        "how ",
        "when ",
        "where ",
        "who ",
        "which ",
        "whose ",
        "can ",
        "could ",
        "would ",
        "should ",
        "is ",
        "are ",
        "was ",
        "were ",
        "do ",
        "does ",
        "did ",
        "will ",
    )

    if text.startswith(
        question_starts
    ):

        return "question"

    if text.endswith("?"):

        return "question"

    return "conversation"


# ============================================================
# FOLLOW-UP CONTEXT
# ============================================================

def _follow_up_context() -> str:

    previous = get_previous_turn()

    if not previous["user"]:

        return ""

    return (
        "PREVIOUS TURN:\n"
        f"User: {previous['user']}\n"
        f"NOVA: {previous['assistant']}"
    )


# ============================================================
# MESSAGE BUILDER
# ============================================================

def _messages(
    user_input: str,
) -> list[dict[str, str]]:

    initialize_model()

    context = build_context()

    previous_turn = (
        _follow_up_context()
    )

    current_time = (
        datetime.now()
        .astimezone()
        .isoformat()
    )

    system_parts = [
        SYSTEM_PROMPT,
        "CURRENT USER:",
        "Saksham",
        "CURRENT TIME:",
        current_time,
        "CURRENT INTENT:",
        classify_intent(
            user_input
        ),
    ]

    if context:

        system_parts.extend(
            [
                "SUPPLIED PERSONAL CONTEXT:",
                context,
            ]
        )

    if previous_turn:

        system_parts.extend(
            [
                "FOLLOW-UP CONTEXT:",
                previous_turn,
            ]
        )

    system_parts.extend(
        [
            "IMPORTANT:",
            (
                "Answer the user's actual question. "
                "Do not reject topics because they are "
                "unrelated to Saksham's work."
            ),
            (
                "Use conversation history when resolving "
                "follow-up references."
            ),
        ]
    )

    system = "\n\n".join(
        system_parts
    )

    messages: list[
        dict[str, str]
    ] = [
        {
            "role": "system",
            "content": system,
        }
    ]

    with _lock:

        messages.extend(
            list(_history)
        )

    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    return messages


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def _is_duplicate_response(
    response: str,
) -> bool:

    if not response:

        return False

    normalized = _normalize(
        response
    )

    with _lock:

        assistant_messages = [
            item["content"]
            for item in _history
            if item["role"] == "assistant"
        ]

    if not assistant_messages:

        return False

    previous = _normalize(
        assistant_messages[-1]
    )

    return (
        previous == normalized
    )


# ============================================================
# OLLAMA GENERATION
# ============================================================

def _generate(
    messages: list[dict[str, str]],
) -> str:

    client = _client()

    response = client.chat(
        model=MODEL_NAME,
        messages=messages,
        options={
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "repeat_penalty": REPEAT_PENALTY,
            "num_ctx": NUM_CTX,
        },
    )

    message = getattr(
        response,
        "message",
        None,
    )

    if message is None:

        raise RuntimeError(
            "Ollama returned no message."
        )

    content = getattr(
        message,
        "content",
        None,
    )

    if content is None:

        raise RuntimeError(
            "Ollama returned empty content."
        )

    return str(
        content
    )


# ============================================================
# RETRY
# ============================================================

def _generate_with_retry(
    messages: list[dict[str, str]],
) -> str:

    global _retry_count

    last_error: Optional[
        Exception
    ] = None

    for attempt in range(
        MAX_RETRIES + 1
    ):

        try:

            return _generate(
                messages
            )

        except Exception as error:

            last_error = error

            logger.warning(
                "Generation attempt %d failed: %s",
                attempt + 1,
                error,
            )

            if attempt >= MAX_RETRIES:

                break

            _retry_count += 1

            time.sleep(
                0.5 * (attempt + 1)
            )

    raise RuntimeError(
        "NOVA generation failed: "
        + str(last_error)
    )


# ============================================================
# STARTUP MESSAGE DETECTION
# ============================================================

def _is_startup_message(
    text: str,
) -> bool:

    normalized = _normalize(
        text
    )

    patterns = {
        "nova is ready",
        "hello saksham nova is ready",
        "hello saksham nova is ready what can i do for you",
        "hello saksham nova is ready what can i do for you boss",
    }

    return normalized in patterns


# ============================================================
# MAIN AI API
# ============================================================

def ask_nova(
    user_input: str,
    user_name: Optional[str] = None,
) -> str:

    global _last_response
    global _last_user_input
    global _last_error
    global _last_request_time
    global _last_response_time
    global _total_requests
    global _successful_requests
    global _failed_requests

    initialize_model()

    if user_input is None:

        return ""

    user_input = str(
        user_input
    ).strip()

    if not user_input:

        return ""

    _total_requests += 1

    _last_request_time = (
        time.time()
    )

    start_time = (
        time.perf_counter()
    )

    _last_user_input = (
        user_input
    )

    # --------------------------------------------------------
    # Startup protection
    # --------------------------------------------------------

    if _is_startup_message(
        user_input
    ):

        response = (
            "I'm ready, Saksham. "
            "What would you like me to do?"
        )

        _add_history(
            "user",
            user_input,
        )

        _add_history(
            "assistant",
            response,
        )

        _last_response = response

        _successful_requests += 1

        _last_response_time = (
            time.perf_counter()
            - start_time
        )

        return response

    # --------------------------------------------------------
    # Check local model
    # --------------------------------------------------------

    status = check_model()

    if not status.get(
        "model_available",
        False,
    ):

        _failed_requests += 1

        raise RuntimeError(
            f"Local model '{MODEL_NAME}' "
            "is unavailable. "
            "Run `ollama list` to check it."
        )

    runtime.thinking = True

    try:

        messages = _messages(
            user_input
        )

        raw_response = (
            _generate_with_retry(
                messages
            )
        )

        response = clean_response(
            raw_response
        )

        if not response:

            raise RuntimeError(
                "NOVA generated an empty response."
            )

        # ----------------------------------------------------
        # Duplicate response recovery
        # ----------------------------------------------------

        if _is_duplicate_response(
            response
        ):

            retry_messages = list(
                messages
            )

            retry_messages.append(
                {
                    "role": "user",
                    "content": (
                        "Give a fresh answer to "
                        "the user's latest request. "
                        "Do not repeat your previous "
                        "answer."
                    ),
                }
            )

            retry_response = (
                _generate_with_retry(
                    retry_messages
                )
            )

            retry_response = clean_response(
                retry_response
            )

            if retry_response:

                response = retry_response

        # ----------------------------------------------------
        # Store conversation
        # ----------------------------------------------------

        _add_history(
            "user",
            user_input,
        )

        _add_history(
            "assistant",
            response,
        )

        _last_response = response

        _last_error = None

        _successful_requests += 1

        return response

    except Exception as error:

        _failed_requests += 1

        _last_error = str(
            error
        )

        logger.error(
            "AI request failed: %s",
            error,
        )

        raise

    finally:

        runtime.thinking = False

        _last_response_time = (
            time.perf_counter()
            - start_time
        )


# ============================================================
# SIMPLE CHAT API
# ============================================================

def chat(
    message: str,
) -> str:

    return ask_nova(
        message
    )


# ============================================================
# BRAIN STATUS
# ============================================================

def get_brain_status() -> dict[str, Any]:

    status = check_model()

    with _lock:

        history_count = len(
            _history
        )

        persistent_count = len(
            _persisted_history
        )

    return {
        "success": status.get(
            "success",
            False,
        ),
        "ollama": status.get(
            "ollama",
            False,
        ),
        "model": MODEL_NAME,
        "model_available": status.get(
            "model_available",
            False,
        ),
        "user": CANONICAL_USER_NAME,
        "assistant": NOVA_NAME,
        "history_messages": history_count,
        "persistent_messages": persistent_count,
        "total_requests": _total_requests,
        "successful_requests": (
            _successful_requests
        ),
        "failed_requests": (
            _failed_requests
        ),
        "retry_count": _retry_count,
        "last_response_time": (
            _last_response_time
        ),
        "last_error": _last_error,
        "thinking": runtime.thinking,
        "speaking": runtime.speaking,
        "listening": runtime.listening,
        "executing_tool": runtime.executing_tool,
    }


# ============================================================
# DIAGNOSTICS
# ============================================================

def diagnostics() -> dict[str, Any]:

    return {
        "assistant": NOVA_NAME,
        "user": CANONICAL_USER_NAME,
        "model": MODEL_NAME,
        "ollama_host": (
            OLLAMA_HOST
            or "default"
        ),
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "repeat_penalty": REPEAT_PENALTY,
        "num_ctx": NUM_CTX,
        "max_history_messages": (
            MAX_HISTORY_MESSAGES
        ),
        "max_context_chars": (
            MAX_CONTEXT_CHARS
        ),
        "max_response_chars": (
            MAX_RESPONSE_CHARS
        ),
        "persistent_file": str(
            CONVERSATION_FILE
        ),
    }


# ============================================================
# SELF TEST
# ============================================================

def self_test() -> dict[str, Any]:

    result: dict[str, Any] = {
        "success": False,
        "ollama": False,
        "model_available": False,
        "profile": False,
        "conscience": False,
        "memory": False,
        "persistent_storage": False,
        "user": CANONICAL_USER_NAME,
        "model": MODEL_NAME,
    }

    initialize_model()

    # --------------------------------------------------------
    # Ollama
    # --------------------------------------------------------

    try:

        status = check_model()

        result["ollama"] = bool(
            status.get(
                "ollama",
                False,
            )
        )

        result["model_available"] = bool(
            status.get(
                "model_available",
                False,
            )
        )

        if not result[
            "model_available"
        ]:

            result["error"] = status

    except Exception as error:

        result["error"] = str(
            error
        )

    # --------------------------------------------------------
    # Profile
    # --------------------------------------------------------

    try:

        name = get_user_name()

        result["profile"] = (
            name == CANONICAL_USER_NAME
        )

    except Exception as error:

        logger.warning(
            "Profile test failed: %s",
            error,
        )

    # --------------------------------------------------------
    # Conscience
    # --------------------------------------------------------

    try:

        build_personal_context()

        result["conscience"] = True

    except Exception as error:

        logger.warning(
            "Conscience test failed: %s",
            error,
        )

    # --------------------------------------------------------
    # Memory
    # --------------------------------------------------------

    try:

        get_all_memories()

        result["memory"] = True

    except Exception as error:

        logger.warning(
            "Memory test failed: %s",
            error,
        )

    # --------------------------------------------------------
    # Persistent storage
    # --------------------------------------------------------

    try:

        DATA_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        result[
            "persistent_storage"
        ] = DATA_DIRECTORY.exists()

    except Exception as error:

        logger.warning(
            "Persistent storage test failed: %s",
            error,
        )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    result["success"] = (
        result["ollama"]
        and result["model_available"]
        and result["profile"]
        and result["persistent_storage"]
    )

    return result


# ============================================================
# CONVERSATION MEMORY UTILITIES
# ============================================================

def remember_current_conversation() -> int:

    initialize_model()

    with _lock:

        _save_persistent_history()

        return len(
            _persisted_history
        )


def forget_conversation() -> None:

    clear_history(
        clear_persistent=True
    )


def conversation_size() -> dict[str, int]:

    with _lock:

        return {
            "current": len(
                _history
            ),
            "persistent": len(
                _persisted_history
            ),
        }


# ============================================================
# MODULE STARTUP
# ============================================================

initialize_model()


# ============================================================
# COMMAND-LINE SELF TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 64)
    print("NOVA — ADVANCED LOCAL AI MODEL")
    print("=" * 64)

    result = self_test()

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )

    print()
    print("Diagnostics:")

    for key, value in diagnostics().items():

        print(
            f"{key}: {value}"
        )

    print()
    print("Conversation:")

    for key, value in conversation_size().items():

        print(
            f"{key}: {value}"
        )

    print("=" * 64)
