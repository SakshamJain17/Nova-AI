from __future__ import annotations

"""
============================================================
NOVA ADVANCED TOOL ROUTER
============================================================

Routes natural-language commands from NOVA's LLM to the
appropriate functions inside system_tools.py.

Designed for:
    • Ollama / Qwen
    • Local-first operation
    • macOS
    • Python 3.12+
    • Voice or text commands
    • JSON tool calls from LLM
    • Natural-language fallback routing
    • Argument extraction
    • Tool validation
    • Confirmation for dangerous operations
    • Conversation-friendly results

Architecture:

    USER
      ↓
    ROUTER
      ↓
    Intent Detection
      ↓
    Tool Selection
      ↓
    Argument Validation
      ↓
    SYSTEM TOOL
      ↓
    Result
      ↓
    NOVA / LLM
"""

import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from . import system_tools


# ============================================================
# TOOL RESULT TYPE
# ============================================================

@dataclass
class RouteResult:
    success: bool
    tool: str | None = None
    result: dict[str, Any] | None = None
    message: str = ""
    requires_confirmation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "tool": self.tool,
            "result": self.result,
            "message": self.message,
            "requires_confirmation": self.requires_confirmation,
        }


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOLS: dict[str, Callable[..., dict]] = {

    # --------------------------------------------------------
    # System
    # --------------------------------------------------------

    "get_system_info":
        system_tools.get_system_info,

    "get_installed_applications":
        system_tools.get_installed_applications,

    "is_application_installed":
        system_tools.is_application_installed,

    "get_battery_status":
        system_tools.get_battery_status,

    "get_datetime":
        system_tools.get_datetime,

    "get_active_application":
        system_tools.get_active_application,

    "get_tool_status":
        system_tools.get_tool_status,

    # --------------------------------------------------------
    # Applications
    # --------------------------------------------------------

    "open_application":
        system_tools.open_application,

    "close_application":
        system_tools.close_application,

    # --------------------------------------------------------
    # Websites
    # --------------------------------------------------------

    "open_website":
        system_tools.open_website,

    "open_website_new_tab":
        system_tools.open_website_new_tab,

    "open_shortcut":
        system_tools.open_shortcut,

    # --------------------------------------------------------
    # Files / folders
    # --------------------------------------------------------

    "open_folder":
        system_tools.open_folder,

    "open_home_folder":
        system_tools.open_home_folder,

    "create_text_file":
        system_tools.create_text_file,

    # --------------------------------------------------------
    # Clipboard
    # --------------------------------------------------------

    "get_clipboard":
        system_tools.get_clipboard,

    "set_clipboard":
        system_tools.set_clipboard,

    # --------------------------------------------------------
    # Audio
    # --------------------------------------------------------

    "set_volume":
        system_tools.set_volume,

    "mute_audio":
        system_tools.mute_audio,

    "unmute_audio":
        system_tools.unmute_audio,

    # --------------------------------------------------------
    # Utilities
    # --------------------------------------------------------

    "calculate":
        system_tools.calculate,

    "take_screenshot":
        system_tools.take_screenshot,

    # --------------------------------------------------------
    # Power
    # --------------------------------------------------------

    "lock_mac":
        system_tools.lock_mac,

    # --------------------------------------------------------
    # Shell
    # --------------------------------------------------------

    "run_shell_command":
        system_tools.run_shell_command,
}


# ============================================================
# NATURAL LANGUAGE TOOL ALIASES
# ============================================================

INTENT_ALIASES: dict[str, list[str]] = {

    "open_application": [
        "open",
        "launch",
        "start",
        "run",
        "activate",
        "open app",
        "launch app",
    ],

    "close_application": [
        "close",
        "quit",
        "exit",
        "stop",
        "shut",
        "close app",
        "quit app",
    ],

    "open_website": [
        "open website",
        "open site",
        "go to website",
        "go to site",
        "visit",
        "browse",
        "navigate to",
    ],

    "open_website_new_tab": [
        "new tab",
        "open in new tab",
        "new browser tab",
        "open website in new tab",
    ],

    "open_folder": [
        "open folder",
        "open directory",
        "show folder",
        "go to folder",
    ],

    "open_home_folder": [
        "open home",
        "open home folder",
        "my home folder",
        "show home",
    ],

    "get_clipboard": [
        "clipboard",
        "what is on my clipboard",
        "read clipboard",
        "show clipboard",
        "pasteboard",
    ],

    "set_clipboard": [
        "copy",
        "copy this",
        "put on clipboard",
        "set clipboard",
        "save to clipboard",
    ],

    "set_volume": [
        "set volume",
        "volume to",
        "change volume",
        "turn volume to",
    ],

    "mute_audio": [
        "mute",
        "mute audio",
        "mute sound",
        "silence",
    ],

    "unmute_audio": [
        "unmute",
        "unmute audio",
        "restore sound",
        "turn sound on",
    ],

    "get_battery_status": [
        "battery",
        "battery status",
        "battery percentage",
        "how much battery",
        "how much charge",
        "charging",
    ],

    "get_datetime": [
        "time",
        "date",
        "what time is it",
        "what is the time",
        "what date is it",
        "today's date",
        "current time",
        "current date",
    ],

    "calculate": [
        "calculate",
        "compute",
        "solve",
        "what is",
        "how much is",
        "plus",
        "minus",
        "multiplied by",
        "divided by",
    ],

    "take_screenshot": [
        "screenshot",
        "take screenshot",
        "capture screen",
        "capture my screen",
        "screen capture",
    ],

    "get_active_application": [
        "active app",
        "current app",
        "frontmost app",
        "what app is open",
        "which app is active",
    ],

    "get_system_info": [
        "system information",
        "system info",
        "computer information",
        "mac information",
        "mac specs",
        "computer specs",
        "about my mac",
    ],

    "get_installed_applications": [
        "installed apps",
        "installed applications",
        "what apps are installed",
        "list applications",
    ],

    "is_application_installed": [
        "is installed",
        "do I have",
        "is app installed",
        "check application",
    ],

    "create_text_file": [
        "create text file",
        "make text file",
        "create a file",
        "write file",
        "save text",
    ],

    "lock_mac": [
        "lock mac",
        "lock my mac",
        "lock computer",
        "lock screen",
    ],

    "run_shell_command": [
        "run command",
        "execute command",
        "terminal command",
        "shell command",
    ],
}


# ============================================================
# DANGEROUS TOOLS
# ============================================================

DANGEROUS_TOOLS = {
    "close_application",
    "lock_mac",
    "run_shell_command",
}


# ============================================================
# ROUTER CLASS
# ============================================================

class NOVARouter:

    def __init__(
        self,
        llm: Any | None = None,
        require_confirmation: bool = True,
    ):
        self.llm = llm
        self.require_confirmation = require_confirmation

        self.pending_action: dict[str, Any] | None = None

    # ========================================================
    # PUBLIC ENTRY POINT
    # ========================================================

    def route(
        self,
        user_input: str,
    ) -> RouteResult:

        if not user_input:
            return RouteResult(
                success=False,
                message="I didn't receive a command.",
            )

        text = user_input.strip()

        # ----------------------------------------------------
        # Confirmation handling
        # ----------------------------------------------------

        confirmation = self._handle_confirmation(text)

        if confirmation is not None:
            return confirmation

        # ----------------------------------------------------
        # First try deterministic routing
        # ----------------------------------------------------

        intent = self.detect_intent(text)

        if intent:

            arguments = self.extract_arguments(
                intent,
                text,
            )

            return self.execute(
                intent,
                arguments,
            )

        # ----------------------------------------------------
        # Try LLM structured routing
        # ----------------------------------------------------

        if self.llm:

            llm_route = self._llm_route(text)

            if llm_route:

                return self.execute(
                    llm_route["tool"],
                    llm_route.get(
                        "arguments",
                        {},
                    ),
                )

        return RouteResult(
            success=False,
            message=(
                "I understood the command, "
                "but I couldn't determine which "
                "system action to perform."
            ),
        )

    # ========================================================
    # INTENT DETECTION
    # ========================================================

    def detect_intent(
        self,
        text: str,
    ) -> str | None:

        normalized = self._normalize(text)

        # ----------------------------------------------------
        # Specific intents first
        # ----------------------------------------------------

        priority = [
            "open_website_new_tab",
            "open_home_folder",
            "get_active_application",
            "get_battery_status",
            "get_system_info",
            "get_installed_applications",
            "is_application_installed",
            "create_text_file",
            "set_clipboard",
            "get_clipboard",
            "set_volume",
            "mute_audio",
            "unmute_audio",
            "take_screenshot",
            "lock_mac",
            "close_application",
            "open_application",
            "open_folder",
            "open_shortcut",
            "open_website",
            "calculate",
            "run_shell_command",
        ]

        # ----------------------------------------------------
        # Exact phrase matching
        # ----------------------------------------------------

        for tool in priority:

            aliases = INTENT_ALIASES.get(
                tool,
                [],
            )

            for alias in aliases:

                if alias in normalized:

                    return tool

        # ----------------------------------------------------
        # Heuristic routing
        # ----------------------------------------------------

        if self._looks_like_calculation(
            normalized
        ):
            return "calculate"

        if self._looks_like_url(
            normalized
        ):
            return "open_website"

        return None

    # ========================================================
    # ARGUMENT EXTRACTION
    # ========================================================

    def extract_arguments(
        self,
        tool: str,
        text: str,
    ) -> dict[str, Any]:

        original = text.strip()

        # ----------------------------------------------------
        # Application
        # ----------------------------------------------------

        if tool in {
            "open_application",
            "close_application",
            "is_application_installed",
        }:

            value = self._extract_application(
                original
            )

            return {
                "application": value
            }

        # ----------------------------------------------------
        # Website
        # ----------------------------------------------------

        if tool in {
            "open_website",
            "open_website_new_tab",
        }:

            url = self._extract_url(
                original
            )

            if not url:

                shortcut = self._extract_website_name(
                    original
                )

                if shortcut:

                    return {
                        "url": shortcut
                    }

            return {
                "url": url or original
            }

        # ----------------------------------------------------
        # Folder
        # ----------------------------------------------------

        if tool == "open_folder":

            folder = self._extract_folder(
                original
            )

            return {
                "folder": folder
            }

        # ----------------------------------------------------
        # Clipboard
        # ----------------------------------------------------

        if tool == "set_clipboard":

            content = self._extract_after_keywords(
                original,
                [
                    "copy",
                    "copy this",
                    "put on clipboard",
                    "set clipboard",
                    "save to clipboard",
                ],
            )

            return {
                "text": content
            }

        # ----------------------------------------------------
        # Volume
        # ----------------------------------------------------

        if tool == "set_volume":

            match = re.search(
                r"(\d+(?:\.\d+)?)\s*%?",
                original,
            )

            return {
                "level": float(match.group(1))
                if match
                else 50
            }

        # ----------------------------------------------------
        # Calculator
        # ----------------------------------------------------

        if tool == "calculate":

            expression = self._extract_expression(
                original
            )

            return {
                "expression": expression
            }

        # ----------------------------------------------------
        # Screenshot
        # ----------------------------------------------------

        if tool == "take_screenshot":

            filename = self._extract_filename(
                original
            )

            return {
                "filename": filename
            }

        # ----------------------------------------------------
        # Text file
        # ----------------------------------------------------

        if tool == "create_text_file":

            return self._extract_file_arguments(
                original
            )

        # ----------------------------------------------------
        # Shell
        # ----------------------------------------------------

        if tool == "run_shell_command":

            command = self._extract_after_keywords(
                original,
                [
                    "run command",
                    "execute command",
                    "terminal command",
                    "shell command",
                ],
            )

            return {
                "command": command
            }

        return {}

    # ========================================================
    # TOOL EXECUTION
    # ========================================================

    def execute(
        self,
        tool: str,
        arguments: dict[str, Any] | None = None,
    ) -> RouteResult:

        arguments = arguments or {}

        # ----------------------------------------------------
        # Validate tool
        # ----------------------------------------------------

        function = TOOLS.get(tool)

        if function is None:

            return RouteResult(
                success=False,
                tool=tool,
                message=f"Unknown tool: {tool}",
            )

        # ----------------------------------------------------
        # Validate arguments
        # ----------------------------------------------------

        validation_error = self.validate_arguments(
            tool,
            arguments,
        )

        if validation_error:

            return RouteResult(
                success=False,
                tool=tool,
                message=validation_error,
            )

        # ----------------------------------------------------
        # Confirmation
        # ----------------------------------------------------

        if (
            self.require_confirmation
            and tool in DANGEROUS_TOOLS
        ):

            self.pending_action = {
                "tool": tool,
                "arguments": arguments,
            }

            return RouteResult(
                success=False,
                tool=tool,
                message=(
                    self._confirmation_message(
                        tool,
                        arguments,
                    )
                ),
                requires_confirmation=True,
            )

        # ----------------------------------------------------
        # Execute
        # ----------------------------------------------------

        try:

            result = function(
                **arguments
            )

            success = bool(
                result.get(
                    "success",
                    False,
                )
            )

            return RouteResult(
                success=success,
                tool=tool,
                result=result,
                message=self._humanize_result(
                    tool,
                    result,
                ),
            )

        except TypeError as error:

            return RouteResult(
                success=False,
                tool=tool,
                message=(
                    f"Invalid arguments for {tool}: "
                    f"{error}"
                ),
            )

        except Exception as error:

            return RouteResult(
                success=False,
                tool=tool,
                message=(
                    f"{tool} failed: {error}"
                ),
            )

    # ========================================================
    # CONFIRMATION
    # ========================================================

    def _handle_confirmation(
        self,
        text: str,
    ) -> RouteResult | None:

        if not self.pending_action:
            return None

        normalized = self._normalize(
            text
        )

        positive = {
            "yes",
            "yeah",
            "yep",
            "sure",
            "do it",
            "confirm",
            "go ahead",
            "okay",
            "ok",
        }

        negative = {
            "no",
            "nope",
            "cancel",
            "stop",
            "don't",
            "do not",
        }

        if normalized in positive:

            action = self.pending_action

            self.pending_action = None

            return self._execute_confirmed(
                action
            )

        if normalized in negative:

            self.pending_action = None

            return RouteResult(
                success=False,
                message="Action cancelled.",
            )

        return RouteResult(
            success=False,
            message=(
                "Please say yes to confirm "
                "or no to cancel."
            ),
            requires_confirmation=True,
        )

    def _execute_confirmed(
        self,
        action: dict[str, Any],
    ) -> RouteResult:

        tool = action["tool"]
        arguments = action["arguments"]

        function = TOOLS[tool]

        try:

            result = function(
                **arguments
            )

            return RouteResult(
                success=result.get(
                    "success",
                    False,
                ),
                tool=tool,
                result=result,
                message=self._humanize_result(
                    tool,
                    result,
                ),
            )

        except Exception as error:

            return RouteResult(
                success=False,
                tool=tool,
                message=str(error),
            )

    # ========================================================
    # ARGUMENT VALIDATION
    # ========================================================

    def validate_arguments(
        self,
        tool: str,
        arguments: dict[str, Any],
    ) -> str | None:

        required: dict[str, list[str]] = {

            "open_application": [
                "application"
            ],

            "close_application": [
                "application"
            ],

            "is_application_installed": [
                "application"
            ],

            "open_website": [
                "url"
            ],

            "open_website_new_tab": [
                "url"
            ],

            "open_folder": [
                "folder"
            ],

            "set_clipboard": [
                "text"
            ],

            "set_volume": [
                "level"
            ],

            "calculate": [
                "expression"
            ],

            "create_text_file": [
                "filename",
                "content",
            ],

            "run_shell_command": [
                "command"
            ],
        }

        for argument in required.get(
            tool,
            [],
        ):

            value = arguments.get(
                argument
            )

            if value is None:

                return (
                    f"Missing required argument: "
                    f"{argument}"
                )

            if isinstance(
                value,
                str,
            ) and not value.strip():

                return (
                    f"Argument '{argument}' "
                    "cannot be empty."
                )

        # ----------------------------------------------------
        # Volume validation
        # ----------------------------------------------------

        if tool == "set_volume":

            try:

                level = float(
                    arguments["level"]
                )

                if not 0 <= level <= 100:

                    return (
                        "Volume must be between "
                        "0 and 100."
                    )

            except (
                ValueError,
                TypeError,
            ):

                return "Invalid volume level."

        # ----------------------------------------------------
        # Shell validation
        # ----------------------------------------------------

        if tool == "run_shell_command":

            command = str(
                arguments["command"]
            ).strip()

            if not command:

                return "Shell command cannot be empty."

        return None

    # ========================================================
    # LLM ROUTER
    # ========================================================

    def _llm_route(
        self,
        text: str,
    ) -> dict[str, Any] | None:

        if not self.llm:
            return None

        prompt = self._build_router_prompt(
            text
        )

        try:

            response = self.llm(
                prompt
            )

            if isinstance(
                response,
                dict,
            ):

                content = (
                    response.get(
                        "response"
                    )
                    or response.get(
                        "content"
                    )
                    or response
                )

            else:

                content = str(
                    response
                )

            parsed = self._extract_json(
                content
            )

            if not parsed:
                return None

            tool = parsed.get(
                "tool"
            )

            if tool not in TOOLS:
                return None

            return {
                "tool": tool,
                "arguments": parsed.get(
                    "arguments",
                    {},
                ),
            }

        except Exception:

            return None

    # ========================================================
    # LLM PROMPT
    # ========================================================

    def _build_router_prompt(
        self,
        user_input: str,
    ) -> str:

        available_tools = list(
            TOOLS.keys()
        )

        return f"""
You are NOVA's system tool router.

Your job is ONLY to determine which local
macOS tool should execute the user's request.

Available tools:

{json.dumps(available_tools, indent=2)}

Return ONLY valid JSON.

Format:

{{
    "tool": "tool_name",
    "arguments": {{
        "argument": "value"
    }}
}}

If the user is not asking for a system action,
return:

{{
    "tool": null,
    "arguments": {{}}
}}

Rules:

1. Never invent tool names.
2. Never include explanations.
3. Preserve user-provided values.
4. Extract application names accurately.
5. Extract URLs accurately.
6. For calculations return the mathematical expression.
7. Do not execute commands yourself.
8. The router executes the selected tool.

User request:

{user_input}
"""

    # ========================================================
    # RESULT HUMANIZATION
    # ========================================================

    def _humanize_result(
        self,
        tool: str,
        result: dict[str, Any],
    ) -> str:

        if not result:

            return "Done."

        if not result.get(
            "success",
            False,
        ):

            return (
                result.get(
                    "error"
                )
                or "The operation failed."
            )

        # ----------------------------------------------------
        # Calculator
        # ----------------------------------------------------

        if tool == "calculate":

            return (
                f"The answer is "
                f"{result.get('result')}."
            )

        # ----------------------------------------------------
        # Battery
        # ----------------------------------------------------

        if tool == "get_battery_status":

            percentage = result.get(
                "percentage"
            )

            charging = result.get(
                "charging"
            )

            if percentage is not None:

                state = (
                    "charging"
                    if charging
                    else "not charging"
                )

                return (
                    f"Battery is at "
                    f"{percentage}%, "
                    f"{state}."
                )

        # ----------------------------------------------------
        # Date/time
        # ----------------------------------------------------

        if tool == "get_datetime":

            return result.get(
                "formatted",
                "I retrieved the current date and time.",
            )

        # ----------------------------------------------------
        # Active application
        # ----------------------------------------------------

        if tool == "get_active_application":

            return (
                f"{result.get('application')} "
                "is currently active."
            )

        # ----------------------------------------------------
        # Generic message
        # ----------------------------------------------------

        if result.get("message"):

            return result["message"]

        return "Done."

    # ========================================================
    # CONFIRMATION MESSAGE
    # ========================================================

    def _confirmation_message(
        self,
        tool: str,
        arguments: dict[str, Any],
    ) -> str:

        if tool == "lock_mac":

            return (
                "This will lock your Mac. "
                "Should I continue?"
            )

        if tool == "close_application":

            return (
                f"This will close "
                f"{arguments.get('application')}. "
                "Should I continue?"
            )

        if tool == "run_shell_command":

            return (
                "This will execute a shell command "
                f"on your Mac:\n\n"
                f"{arguments.get('command')}\n\n"
                "Should I continue?"
            )

        return "Should I continue?"

    # ========================================================
    # NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:

        text = text.lower().strip()

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text

    # ========================================================
    # APPLICATION EXTRACTION
    # ========================================================

    def _extract_application(
        self,
        text: str,
    ) -> str:

        cleaned = text.strip()

        patterns = [
            r"(?:open|launch|start|run|activate)\s+(.+)",
            r"(?:close|quit|exit|stop|shut)\s+(.+)",
            r"(?:is|do i have)\s+(.+?)\s+(?:installed)?$",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                cleaned,
                re.IGNORECASE,
            )

            if match:

                value = match.group(1).strip()

                value = re.sub(
                    r"\bplease\b",
                    "",
                    value,
                    flags=re.IGNORECASE,
                )

                value = value.strip(
                    " .?!"
                )

                return value

        return cleaned

    # ========================================================
    # URL EXTRACTION
    # ========================================================

    def _extract_url(
        self,
        text: str,
    ) -> str | None:

        match = re.search(
            r"(https?://[^\s]+)",
            text,
            re.IGNORECASE,
        )

        if match:

            return match.group(1).rstrip(
                ".,!?;:"
            )

        domain = re.search(
            r"\b([a-zA-Z0-9-]+\.)"
            r"+[a-zA-Z]{2,}(?:/[^\s]*)?",
            text,
        )

        if domain:

            return domain.group(0).rstrip(
                ".,!?;:"
            )

        return None

    # ========================================================
    # WEBSITE NAME
    # ========================================================

    def _extract_website_name(
        self,
        text: str,
    ) -> str | None:

        normalized = self._normalize(
            text
        )

        for shortcut in system_tools.WEBSITE_SHORTCUTS:

            if shortcut in normalized:

                return shortcut

        return None

    # ========================================================
    # FOLDER EXTRACTION
    # ========================================================

    def _extract_folder(
        self,
        text: str,
    ) -> str:

        value = self._extract_after_keywords(
            text,
            [
                "open folder",
                "open directory",
                "show folder",
                "go to folder",
            ],
        )

        value = value.strip(
            "\"'"
        )

        aliases = {
            "desktop":
                "~/Desktop",

            "downloads":
                "~/Downloads",

            "documents":
                "~/Documents",

            "documents folder":
                "~/Documents",

            "downloads folder":
                "~/Downloads",

            "desktop folder":
                "~/Desktop",
        }

        return aliases.get(
            value.lower(),
            value,
        )

    # ========================================================
    # EXPRESSION EXTRACTION
    # ========================================================

    def _extract_expression(
        self,
        text: str,
    ) -> str:

        value = self._extract_after_keywords(
            text,
            [
                "calculate",
                "compute",
                "solve",
                "what is",
                "how much is",
            ],
        )

        value = (
            value
            .replace("times", "*")
            .replace("multiplied by", "*")
            .replace("divided by", "/")
            .replace("plus", "+")
            .replace("minus", "-")
            .replace("percent", "%")
        )

        return value.strip(
            " .?!"
        )

    # ========================================================
    # FILE EXTRACTION
    # ========================================================

    def _extract_file_arguments(
        self,
        text: str,
    ) -> dict[str, Any]:

        # Example:
        #
        # create text file hello.txt containing hello world

        match = re.search(
            r"(?:file|text file)\s+"
            r"([^\s]+)"
            r"(?:\s+(?:containing|with|saying)\s+(.+))?",
            text,
            re.IGNORECASE,
        )

        if match:

            filename = match.group(1)

            content = (
                match.group(2)
                or ""
            )

            return {
                "filename": filename,
                "content": content,
            }

        return {
            "filename": "NOVA_Note.txt",
            "content": "",
        }

    # ========================================================
    # FILENAME
    # ========================================================

    def _extract_filename(
        self,
        text: str,
    ) -> str | None:

        match = re.search(
            r"(?:as|named|called)\s+"
            r"([^\s]+)",
            text,
            re.IGNORECASE,
        )

        if match:

            return match.group(1)

        return None

    # ========================================================
    # GENERIC KEYWORD EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_after_keywords(
        text: str,
        keywords: list[str],
    ) -> str:

        lower = text.lower()

        for keyword in sorted(
            keywords,
            key=len,
            reverse=True,
        ):

            index = lower.find(
                keyword.lower()
            )

            if index != -1:

                value = text[
                    index + len(keyword):
                ]

                return value.strip(
                    " :,-"
                )

        return text.strip()

    # ========================================================
    # CALCULATION DETECTION
    # ========================================================

    @staticmethod
    def _looks_like_calculation(
        text: str,
    ) -> bool:

        if re.search(
            r"\d+\s*[\+\-\*\/\%\^]\s*\d+",
            text,
        ):
            return True

        mathematical_words = [
            "plus",
            "minus",
            "times",
            "multiplied",
            "divided",
            "calculate",
            "compute",
        ]

        return any(
            word in text
            for word in mathematical_words
        )

    # ========================================================
    # URL DETECTION
    # ========================================================

    @staticmethod
    def _looks_like_url(
        text: str,
    ) -> bool:

        return bool(
            re.search(
                r"https?://|"
                r"\b[a-zA-Z0-9-]+\."
                r"[a-zA-Z]{2,}",
                text,
            )
        )

    # ========================================================
    # JSON EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_json(
        text: str,
    ) -> dict[str, Any] | None:

        text = text.strip()

        # ----------------------------------------------------
        # Direct JSON
        # ----------------------------------------------------

        try:

            value = json.loads(
                text
            )

            if isinstance(
                value,
                dict,
            ):

                return value

        except Exception:
            pass

        # ----------------------------------------------------
        # JSON inside markdown
        # ----------------------------------------------------

        match = re.search(
            r"```(?:json)?\s*"
            r"(\{.*?\})"
            r"\s*```",
            text,
            re.DOTALL,
        )

        if match:

            try:

                value = json.loads(
                    match.group(1)
                )

                if isinstance(
                    value,
                    dict,
                ):

                    return value

            except Exception:
                pass

        # ----------------------------------------------------
        # Find JSON object
        # ----------------------------------------------------

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end > start:

            try:

                value = json.loads(
                    text[start:end + 1]
                )

                if isinstance(
                    value,
                    dict,
                ):

                    return value

            except Exception:
                pass

        return None


# ============================================================
# GLOBAL ROUTER
# ============================================================

router = NOVARouter(
    require_confirmation=True
)


# ============================================================
# SIMPLE PUBLIC API
# ============================================================

def route_command(
    user_input: str,
) -> dict[str, Any]:

    result = router.route(
        user_input
    )

    return result.to_dict()


def execute_tool(
    tool: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:

    result = router.execute(
        tool,
        arguments,
    )

    return result.to_dict()


# ============================================================
# DEBUG / SELF TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("NOVA ADVANCED ROUTER")
    print("=" * 60)

    tests = [

        "open calculator",

        "launch VS Code",

        "open YouTube",

        "open google.com",

        "open my Downloads folder",

        "what is 25 * 8",

        "what is my battery percentage",

        "what time is it",

        "what application is active",

        "take a screenshot",

        "copy hello NOVA",

        "set volume to 40",

        "mute audio",

        "open Safari in a new tab",

    ]

    for command in tests:

        print()
        print("USER:", command)

        result = route_command(
            command
        )

        print(
            json.dumps(
                result,
                indent=2,
                default=str,
            )
        )