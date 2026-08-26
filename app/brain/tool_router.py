from __future__ import annotations

"""
============================================================
NOVA ADVANCED TOOL ROUTER
============================================================

Architecture:

    User
      |
      v
    NOVA UI
      |
      v
    clean_command()
      |
      v
    deterministic router
      |
      +---- System / App
      +---- Browser
      +---- Files / Folders
      +---- Audio
      +---- Screenshot
      +---- Battery / Time
      +---- Calculator
      +---- Search
      |
      v
    handled == False
      |
      v
    Qwen / LLM

IMPORTANT:
    Deterministic actions happen BEFORE Qwen.

The router should be:
    - predictable
    - fast
    - safe
    - extensible
    - easy to debug
    - independent of the LLM
"""

import os
import re
import subprocess
import urllib.parse
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


# ============================================================
# SYSTEM TOOLS
# ============================================================

from app.tools.system_tools import (
    open_application,
    close_application,
    open_website,
    open_website_new_tab,
    open_folder,
    get_battery_status,
    get_datetime,
    set_volume,
    mute_audio,
    unmute_audio,
    take_screenshot,
    calculate,
    get_active_application,
)


# ============================================================
# NOVA CONFIGURATION
# ============================================================

USER_NAME = "Saksham"
NOVA_NAME = "NOVA"

HOME = os.path.expanduser("~")


# ============================================================
# APPLICATION ALIASES
# ============================================================

APPLICATIONS: Dict[str, str] = {

    # Apple
    "safari": "Safari",
    "finder": "Finder",
    "terminal": "Terminal",
    "calculator": "Calculator",
    "notes": "Notes",
    "calendar": "Calendar",
    "mail": "Mail",
    "messages": "Messages",
    "facetime": "FaceTime",
    "photos": "Photos",
    "preview": "Preview",
    "music": "Music",
    "quicktime": "QuickTime Player",
    "quicktime player": "QuickTime Player",
    "system settings": "System Settings",
    "settings": "System Settings",

    # Browsers
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "firefox": "Firefox",
    "edge": "Microsoft Edge",
    "microsoft edge": "Microsoft Edge",
    "brave": "Brave Browser",
    "brave browser": "Brave Browser",

    # Development
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "cursor": "Cursor",
    "xcode": "Xcode",
    "pycharm": "PyCharm",
    "android studio": "Android Studio",

    # Communication
    "whatsapp": "WhatsApp",
    "whatsapp desktop": "WhatsApp",
    "discord": "Discord",
    "telegram": "Telegram",
    "slack": "Slack",
    "zoom": "zoom.us",
    "zoom meetings": "zoom.us",
    "microsoft teams": "Microsoft Teams",
    "teams": "Microsoft Teams",

    # Entertainment
    "spotify": "Spotify",
    "netflix": "Netflix",
    "vlc": "VLC",
    "steam": "Steam",

    # Microsoft
    "word": "Microsoft Word",
    "microsoft word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "microsoft excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "microsoft powerpoint": "Microsoft PowerPoint",

    # Productivity
    "notion": "Notion",
    "obsidian": "Obsidian",
    "figma": "Figma",
}


# ============================================================
# WEBSITE ALIASES
# ============================================================

WEBSITES: Dict[str, str] = {

    "youtube": "https://youtube.com",
    "youtube.com": "https://youtube.com",

    "google": "https://google.com",
    "google.com": "https://google.com",

    "gmail": "https://mail.google.com",
    "gmail.com": "https://mail.google.com",

    "whatsapp web": "https://web.whatsapp.com",
    "web whatsapp": "https://web.whatsapp.com",

    "github": "https://github.com",
    "github.com": "https://github.com",

    "chatgpt": "https://chatgpt.com",
    "chat gpt": "https://chatgpt.com",

    "instagram": "https://instagram.com",
    "facebook": "https://facebook.com",
    "linkedin": "https://linkedin.com",
    "reddit": "https://reddit.com",

    "twitter": "https://x.com",
    "x": "https://x.com",

    "amazon": "https://amazon.in",
    "amazon india": "https://amazon.in",

    "netflix": "https://netflix.com",

    "spotify web": "https://open.spotify.com",

    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",

    "wikipedia": "https://wikipedia.org",
}


# ============================================================
# FOLDER ALIASES
# ============================================================

FOLDERS: Dict[str, str] = {

    "home": HOME,
    "home folder": HOME,

    "desktop": os.path.join(HOME, "Desktop"),
    "desktop folder": os.path.join(HOME, "Desktop"),

    "downloads": os.path.join(HOME, "Downloads"),
    "download": os.path.join(HOME, "Downloads"),
    "downloads folder": os.path.join(HOME, "Downloads"),

    "documents": os.path.join(HOME, "Documents"),
    "documents folder": os.path.join(HOME, "Documents"),

    "pictures": os.path.join(HOME, "Pictures"),
    "photos folder": os.path.join(HOME, "Pictures"),

    "movies": os.path.join(HOME, "Movies"),
    "music": os.path.join(HOME, "Music"),
}


# ============================================================
# BROWSER ALIASES
# ============================================================

BROWSERS: Dict[str, str] = {
    "safari": "Safari",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "firefox": "Firefox",
    "edge": "Microsoft Edge",
    "microsoft edge": "Microsoft Edge",
    "brave": "Brave Browser",
    "brave browser": "Brave Browser",
}


# ============================================================
# ROUTER STATE
# ============================================================

@dataclass
class RouterState:
    last_application: Optional[str] = None
    last_website: Optional[str] = None
    last_folder: Optional[str] = None
    last_command: Optional[str] = None
    last_action: Optional[str] = None


_state = RouterState()


# ============================================================
# RESULT HELPERS
# ============================================================

def handled(
    message: str,
    data: Any = None,
    action: Optional[str] = None,
) -> dict:
    _state.last_action = action

    return {
        "handled": True,
        "success": True,
        "message": message,
        "data": data,
        "action": action,
        "router": NOVA_NAME,
    }


def failed(
    message: str,
    data: Any = None,
    action: Optional[str] = None,
) -> dict:
    _state.last_action = action

    return {
        "handled": True,
        "success": False,
        "message": message,
        "data": data,
        "action": action,
        "router": NOVA_NAME,
    }


def not_handled() -> dict:
    return {
        "handled": False,
        "success": False,
        "message": "",
        "data": None,
        "action": None,
        "router": NOVA_NAME,
    }


# ============================================================
# STATE MANAGEMENT
# ============================================================

def remember_application(application: str) -> None:
    _state.last_application = application


def remember_website(url: str) -> None:
    _state.last_website = url


def remember_folder(folder: str) -> None:
    _state.last_folder = folder


def get_last_application() -> Optional[str]:
    return _state.last_application


def get_last_website() -> Optional[str]:
    return _state.last_website


def get_last_folder() -> Optional[str]:
    return _state.last_folder


def get_router_state() -> dict:
    return {
        "last_application": _state.last_application,
        "last_website": _state.last_website,
        "last_folder": _state.last_folder,
        "last_command": _state.last_command,
        "last_action": _state.last_action,
    }


def reset_router_state() -> None:
    global _state
    _state = RouterState()


# ============================================================
# COMMAND CLEANING
# ============================================================

def clean_command(text: str) -> str:
    if not text:
        return ""

    text = str(text).strip()

    # Remove wake words repeatedly.
    wake_words = (
        "hello nova",
        "hey nova",
        "hi nova",
        "okay nova",
        "ok nova",
        "nova",
    )

    changed = True

    while changed:
        changed = False
        lower = text.lower().strip()

        for wake_word in wake_words:

            if lower.startswith(wake_word):

                text = text[len(wake_word):].strip()

                while text and text[0] in ",:;.!?-":
                    text = text[1:].strip()

                changed = True
                break

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    # Remove common polite endings.
    text = re.sub(
        r"\s+(please|for me|thanks|thank you)\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_target(target: str) -> str:
    target = target.lower().strip()

    target = target.rstrip(".,!?;:")

    target = re.sub(
        r"\s+",
        " ",
        target,
    )

    return target


# ============================================================
# APPLICATION RESOLUTION
# ============================================================

def resolve_application(
    target: str,
) -> Optional[str]:

    target = normalize_target(target)

    return APPLICATIONS.get(target)


# ============================================================
# BROWSER RESOLUTION
# ============================================================

def resolve_browser(
    target: str,
) -> Optional[str]:

    target = normalize_target(target)

    return BROWSERS.get(target)


# ============================================================
# WEBSITE RESOLUTION
# ============================================================

def resolve_website(
    target: str,
) -> Optional[str]:

    target = normalize_target(target)

    if target in WEBSITES:
        return WEBSITES[target]

    if target.startswith("https://"):
        return target

    if target.startswith("http://"):
        return target

    # Direct domain.
    if re.fullmatch(
        r"[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        target,
    ):
        return "https://" + target

    return None


# ============================================================
# OPEN URL
# ============================================================

def open_url_in_browser(
    url: str,
    browser: Optional[str] = None,
) -> dict:

    try:

        if browser:

            result = subprocess.run(
                [
                    "open",
                    "-a",
                    browser,
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

        else:

            result = subprocess.run(
                [
                    "open",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

        return {
            "success": result.returncode == 0,
            "url": url,
            "browser": browser,
            "error": result.stderr.strip(),
        }

    except Exception as error:

        return {
            "success": False,
            "url": url,
            "browser": browser,
            "error": str(error),
        }


# ============================================================
# WEBSITE ON SPECIFIC BROWSER
# ============================================================

def handle_website_on_browser(
    command: str,
) -> dict:

    patterns = [

        r"^(?:open|launch|go to|visit)\s+(.+?)\s+on\s+(.+)$",

        r"^(?:open|launch|go to|visit)\s+(.+?)\s+using\s+(.+)$",

    ]

    lower = command.lower().strip()

    for pattern in patterns:

        match = re.search(
            pattern,
            lower,
        )

        if not match:
            continue

        website_target = normalize_target(
            match.group(1)
        )

        browser_target = normalize_target(
            match.group(2)
        )

        browser = resolve_browser(
            browser_target
        )

        if not browser:
            return not_handled()

        url = resolve_website(
            website_target
        )

        if not url:
            return not_handled()

        result = open_url_in_browser(
            url,
            browser,
        )

        if not result.get("success"):

            return failed(
                f"I couldn't open "
                f"{website_target} in "
                f"{browser}.",
                result,
                "open_website_in_browser",
            )

        remember_application(browser)
        remember_website(url)

        return handled(
            f"Done. I opened "
            f"{website_target} in "
            f"{browser}.",
            result,
            "open_website_in_browser",
        )

    return not_handled()


# ============================================================
# WEBSITE HANDLER
# ============================================================

def handle_website(
    command: str,
) -> dict:

    lower = command.lower().strip()

    match = re.search(
        r"^(?:open|launch|go to|visit)\s+(.+)$",
        lower,
    )

    if not match:
        return not_handled()

    target = normalize_target(
        match.group(1)
    )

    # Don't steal application commands.
    if target in APPLICATIONS:
        return not_handled()

    # Don't steal folder commands.
    if target in FOLDERS:
        return not_handled()

    url = resolve_website(target)

    if not url:
        return not_handled()

    try:

        result = open_website_new_tab(url)

    except Exception:

        result = open_url_in_browser(url)

    if result.get("success"):

        remember_website(url)

        return handled(
            f"Done. I opened {target.title()}.",
            result,
            "open_website",
        )

    return failed(
        f"I couldn't open {target}.",
        result,
        "open_website",
    )


# ============================================================
# APPLICATION HANDLER
# ============================================================

def handle_application(
    command: str,
) -> dict:

    lower = command.lower().strip()

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context_commands = {
        "open it",
        "launch it",
        "start it",
        "run it",
        "open that",
        "launch that",
        "start that",
        "run that",
        "open the app",
        "launch the app",
        "start the app",
    }

    if lower in context_commands:

        if not _state.last_application:

            return failed(
                "I don't know which application "
                "you mean.",
                action="open_context_application",
            )

        result = open_application(
            _state.last_application
        )

        if result.get("success"):

            return handled(
                f"Done. "
                f"{_state.last_application} "
                f"is open.",
                result,
                "open_context_application",
            )

        return failed(
            f"I couldn't open "
            f"{_state.last_application}.",
            result,
            "open_context_application",
        )

    # --------------------------------------------------------
    # STANDARD OPEN
    # --------------------------------------------------------

    match = re.search(
        r"^(?:open|launch|start|run)\s+(.+)$",
        lower,
    )

    if not match:
        return not_handled()

    target = normalize_target(
        match.group(1)
    )

    target = re.sub(
        r"\s+(?:application|app)$",
        "",
        target,
    ).strip()

    application = resolve_application(target)

    if not application:
        return not_handled()

    try:

        result = open_application(application)

    except Exception as error:

        return failed(
            f"I couldn't open {application}.",
            {"error": str(error)},
            "open_application",
        )

    if result.get("success"):

        remember_application(application)

        return handled(
            f"Done. {application} is open.",
            result,
            "open_application",
        )

    # WhatsApp fallback.
    if application == "WhatsApp":

        try:

            fallback = open_url_in_browser(
                "https://web.whatsapp.com"
            )

            if fallback.get("success"):

                remember_application(application)
                remember_website(
                    "https://web.whatsapp.com"
                )

                return handled(
                    "WhatsApp Desktop isn't available, "
                    "so I opened WhatsApp Web instead.",
                    fallback,
                    "open_whatsapp_web",
                )

        except Exception:
            pass

    return failed(
        f"I couldn't open {application}.",
        result,
        "open_application",
    )


# ============================================================
# CLOSE APPLICATION
# ============================================================

def handle_close(
    command: str,
) -> dict:

    lower = command.lower().strip()

    match = re.search(
        r"^(?:close|quit|stop|exit)\s+(.+)$",
        lower,
    )

    if not match:
        return not_handled()

    target = normalize_target(
        match.group(1)
    )

    if target in {
        "it",
        "that",
        "the app",
        "the application",
    }:

        if not _state.last_application:

            return failed(
                "I don't know which application "
                "you want me to close.",
                action="close_context_application",
            )

        application = _state.last_application

    else:

        application = (
            resolve_application(target)
            or target
        )

    try:

        result = close_application(
            application
        )

    except Exception as error:

        return failed(
            f"I couldn't close {application}.",
            {"error": str(error)},
            "close_application",
        )

    if result.get("success"):

        return handled(
            f"Done. I closed {application}.",
            result,
            "close_application",
        )

    return failed(
        f"I couldn't close {application}.",
        result,
        "close_application",
    )


# ============================================================
# FOLDER HANDLER
# ============================================================

def handle_folder(
    command: str,
) -> dict:

    lower = command.lower().strip()

    patterns = [

        r"^open\s+(.+?)\s+folder$",

        r"^open\s+(.+)$",

        r"^go to\s+(.+)$",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            lower,
        )

        if not match:
            continue

        target = normalize_target(
            match.group(1)
        )

        if target not in FOLDERS:
            continue

        path = FOLDERS[target]

        try:

            result = open_folder(path)

        except Exception as error:

            return failed(
                f"I couldn't open the {target} folder.",
                {"error": str(error)},
                "open_folder",
            )

        if result.get("success"):

            remember_folder(path)

            return handled(
                f"Done. I opened the {target} folder.",
                result,
                "open_folder",
            )

        return failed(
            f"I couldn't open the {target} folder.",
            result,
            "open_folder",
        )

    return not_handled()


# ============================================================
# SCREENSHOT
# ============================================================

def handle_screenshot(
    command: str,
) -> dict:

    lower = command.lower()

    phrases = {
        "take a screenshot",
        "take screenshot",
        "screenshot",
        "capture my screen",
        "capture the screen",
        "capture screen",
        "take a screen capture",
    }

    if not any(
        phrase in lower
        for phrase in phrases
    ):
        return not_handled()

    try:

        result = take_screenshot()

    except Exception as error:

        return failed(
            "I couldn't take a screenshot.",
            {"error": str(error)},
            "screenshot",
        )

    if result.get("success"):

        return handled(
            "Done. I took a screenshot.",
            result,
            "screenshot",
        )

    return failed(
        "I couldn't take a screenshot.",
        result,
        "screenshot",
    )


# ============================================================
# AUDIO
# ============================================================

def handle_audio(
    command: str,
) -> dict:

    lower = command.lower().strip()

    # --------------------------------------------------------
    # UNMUTE FIRST
    # --------------------------------------------------------

    if "unmute" in lower:

        try:

            result = unmute_audio()

        except Exception as error:

            return failed(
                "I couldn't unmute the Mac.",
                {"error": str(error)},
                "unmute_audio",
            )

        if result.get("success"):

            return handled(
                "Done. Your Mac is unmuted.",
                result,
                "unmute_audio",
            )

        return failed(
            "I couldn't unmute the Mac.",
            result,
            "unmute_audio",
        )

    # --------------------------------------------------------
    # MUTE
    # --------------------------------------------------------

    if "mute" in lower:

        try:

            result = mute_audio()

        except Exception as error:

            return failed(
                "I couldn't mute the Mac.",
                {"error": str(error)},
                "mute_audio",
            )

        if result.get("success"):

            return handled(
                "Done. Your Mac is muted.",
                result,
                "mute_audio",
            )

        return failed(
            "I couldn't mute the Mac.",
            result,
            "mute_audio",
        )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    match = re.search(
        r"(?:set|change)\s+(?:the\s+)?"
        r"volume\s+(?:to\s+)?"
        r"(\d{1,3})",
        lower,
    )

    if match:

        level = int(match.group(1))

        if level < 0 or level > 100:

            return failed(
                "Volume must be between 0 and 100.",
                action="set_volume",
            )

        try:

            result = set_volume(level)

        except Exception as error:

            return failed(
                "I couldn't change the volume.",
                {"error": str(error)},
                "set_volume",
            )

        if result.get("success"):

            return handled(
                f"Done. Volume is now {level}%.",
                result,
                "set_volume",
            )

        return failed(
            "I couldn't change the volume.",
            result,
            "set_volume",
        )

    return not_handled()


# ============================================================
# BATTERY
# ============================================================

def handle_battery(
    command: str,
) -> dict:

    lower = command.lower()

    keywords = [
        "battery",
        "battery percentage",
        "battery level",
        "battery status",
        "how much battery",
        "how much charge",
    ]

    if not any(
        keyword in lower
        for keyword in keywords
    ):
        return not_handled()

    try:

        result = get_battery_status()

    except Exception as error:

        return failed(
            "I couldn't read the battery.",
            {"error": str(error)},
            "battery",
        )

    if not result.get("success"):

        return failed(
            "I couldn't read the battery.",
            result,
            "battery",
        )

    percentage = result.get("percentage")
    charging = result.get("charging")

    if percentage is not None:

        if charging:
            state = "charging"
        else:
            state = "not charging"

        return handled(
            f"Your battery is at "
            f"{percentage}% and is {state}.",
            result,
            "battery",
        )

    return handled(
        "I retrieved your battery status.",
        result,
        "battery",
    )


# ============================================================
# DATE / TIME
# ============================================================

def handle_datetime(
    command: str,
) -> dict:

    lower = command.lower()

    phrases = [
        "what time is it",
        "what is the time",
        "what's the time",
        "current time",
        "tell me the time",
        "what date is it",
        "what is today's date",
        "today's date",
        "date and time",
    ]

    if not any(
        phrase in lower
        for phrase in phrases
    ):
        return not_handled()

    try:

        result = get_datetime()

    except Exception as error:

        return failed(
            "I couldn't get the date and time.",
            {"error": str(error)},
            "datetime",
        )

    formatted = result.get("formatted")

    if formatted:

        return handled(
            f"It is {formatted}.",
            result,
            "datetime",
        )

    return handled(
        "I retrieved the current date and time.",
        result,
        "datetime",
    )


# ============================================================
# CALCULATOR
# ============================================================

def handle_calculation(
    command: str,
) -> dict:

    lower = command.lower().strip()

    patterns = [

        r"^calculate\s+(.+)$",

        r"^compute\s+(.+)$",

        r"^what is\s+([0-9\s+\-*/().%^]+)$",

        r"^what's\s+([0-9\s+\-*/().%^]+)$",

    ]

    expression = None

    for pattern in patterns:

        match = re.search(
            pattern,
            lower,
        )

        if match:

            expression = match.group(1).strip()
            break

    if not expression:
        return not_handled()

    # Only mathematical characters.
    if not re.fullmatch(
        r"[0-9\s+\-*/().%^]+",
        expression,
    ):
        return not_handled()

    try:

        result = calculate(expression)

    except Exception:

        return failed(
            "I couldn't calculate that.",
            action="calculate",
        )

    if not result.get("success"):

        return failed(
            "I couldn't calculate that.",
            result,
            "calculate",
        )

    return handled(
        f"The answer is {result.get('result')}.",
        result,
        "calculate",
    )


# ============================================================
# WEB SEARCH
# ============================================================

def handle_search(
    command: str,
) -> dict:

    lower = command.lower().strip()

    patterns = [

        r"^(?:search|google|look up)\s+(.+)$",

        r"^(?:search for|look for)\s+(.+)$",

    ]

    query = None

    for pattern in patterns:

        match = re.search(
            pattern,
            lower,
        )

        if match:

            query = match.group(1).strip()
            break

    if not query:
        return not_handled()

    encoded = urllib.parse.quote_plus(query)

    url = (
        "https://www.google.com/search?q="
        + encoded
    )

    try:

        result = open_website_new_tab(url)

    except Exception:

        result = open_url_in_browser(url)

    if result.get("success"):

        remember_website(url)

        return handled(
            f"Done. I searched Google for {query}.",
            result,
            "web_search",
        )

    return failed(
        "I couldn't perform the web search.",
        result,
        "web_search",
    )


# ============================================================
# CURRENT APPLICATION
# ============================================================

def handle_current_app(
    command: str,
) -> dict:

    lower = command.lower()

    phrases = [
        "what app is open",
        "what application is open",
        "what am i using",
        "what app am i using",
        "which app is open",
        "what is the active app",
        "what application am i using",
    ]

    if not any(
        phrase in lower
        for phrase in phrases
    ):
        return not_handled()

    try:

        result = get_active_application()

    except Exception as error:

        return failed(
            "I couldn't determine the active application.",
            {"error": str(error)},
            "active_application",
        )

    if not result.get("success"):

        return failed(
            "I couldn't determine the active application.",
            result,
            "active_application",
        )

    application = result.get("application")

    return handled(
        f"The active application is {application}.",
        result,
        "active_application",
    )


# ============================================================
# CONTEXT COMMANDS
# ============================================================

def handle_context_command(
    command: str,
) -> dict:

    lower = command.lower().strip()

    # --------------------------------------------------------
    # OPEN LAST APP
    # --------------------------------------------------------

    if lower in {
        "open it",
        "launch it",
        "start it",
        "run it",
        "open that",
        "launch that",
        "start that",
        "run that",
    }:

        if not _state.last_application:

            return failed(
                "I don't have a previous application "
                "to open yet.",
                action="context_open_app",
            )

        result = open_application(
            _state.last_application
        )

        if result.get("success"):

            return handled(
                f"Done. "
                f"{_state.last_application} "
                f"is open.",
                result,
                "context_open_app",
            )

        return failed(
            f"I couldn't open "
            f"{_state.last_application}.",
            result,
            "context_open_app",
        )

    # --------------------------------------------------------
    # OPEN LAST WEBSITE
    # --------------------------------------------------------

    if lower in {
        "open that website",
        "open the website",
        "open the site",
        "open it in the browser",
        "reopen the website",
        "reopen the site",
    }:

        if not _state.last_website:

            return failed(
                "I don't have a previous website yet.",
                action="context_open_website",
            )

        result = open_website_new_tab(
            _state.last_website
        )

        if result.get("success"):

            return handled(
                "Done. I reopened the website.",
                result,
                "context_open_website",
            )

        return failed(
            "I couldn't reopen the website.",
            result,
            "context_open_website",
        )

    # --------------------------------------------------------
    # CLOSE LAST APP
    # --------------------------------------------------------

    if lower in {
        "close it",
        "close that",
        "close the app",
        "close the application",
    }:

        if not _state.last_application:

            return failed(
                "I don't know which application "
                "you mean.",
                action="context_close_app",
            )

        result = close_application(
            _state.last_application
        )

        if result.get("success"):

            return handled(
                f"Done. I closed "
                f"{_state.last_application}.",
                result,
                "context_close_app",
            )

        return failed(
            f"I couldn't close "
            f"{_state.last_application}.",
            result,
            "context_close_app",
        )

    return not_handled()


# ============================================================
# HELP / CAPABILITIES
# ============================================================

def handle_help(
    command: str,
) -> dict:

    lower = command.lower().strip()

    if lower not in {
        "help",
        "what can you do",
        "what can you do for me",
        "show commands",
        "show me what you can do",
    }:
        return not_handled()

    capabilities = {
        "applications": [
            "open applications",
            "close applications",
            "reopen the last application",
        ],
        "web": [
            "open websites",
            "open websites in specific browsers",
            "Google searches",
        ],
        "files": [
            "open Desktop",
            "open Downloads",
            "open Documents",
            "open Pictures",
            "open Movies",
            "open Music",
        ],
        "system": [
            "battery status",
            "date and time",
            "volume control",
            "mute/unmute",
            "screenshots",
            "active application",
            "calculator",
        ],
    }

    return handled(
        "I can control applications, websites, "
        "folders, audio, screenshots, battery, "
        "date and time, calculations and more.",
        capabilities,
        "help",
    )


# ============================================================
# COMMAND REGISTRY
# ============================================================

HANDLERS: List[Callable[[str], dict]] = [
    # Context first.
    handle_context_command,

    # Help.
    handle_help,

    # Browser-specific.
    handle_website_on_browser,

    # Websites.
    handle_website,

    # Applications.
    handle_application,

    # Close.
    handle_close,

    # Folders.
    handle_folder,

    # System.
    handle_screenshot,
    handle_audio,
    handle_battery,
    handle_datetime,
    handle_calculation,
    handle_current_app,

    # Search should be relatively late.
    handle_search,
]


# ============================================================
# MAIN ROUTER
# ============================================================

def route_command(
    user_input: str,
) -> dict:

    if not user_input:
        return not_handled()

    # --------------------------------------------------------
    # Clean command
    # --------------------------------------------------------

    command = clean_command(user_input)

    if not command:
        return not_handled()

    _state.last_command = command

    # --------------------------------------------------------
    # Debug
    # --------------------------------------------------------

    print(
        f"[ROUTER] {user_input!r}"
        f" -> {command!r}"
    )

    # --------------------------------------------------------
    # Execute handlers
    # --------------------------------------------------------

    for handler in HANDLERS:

        try:

            result = handler(command)

            if result.get("handled"):

                print(
                    "[ROUTER RESULT]",
                    result,
                )

                return result

        except Exception as error:

            print(
                f"[ROUTER ERROR] "
                f"{handler.__name__}: "
                f"{error}"
            )

            return failed(
                "I encountered a system tool error.",
                {
                    "handler": handler.__name__,
                    "error": str(error),
                },
                "router_error",
            )

    # --------------------------------------------------------
    # QWEN FALLBACK
    # --------------------------------------------------------

    print(
        "[ROUTER] No deterministic "
        "system command detected."
    )

    return not_handled()


# ============================================================
# SAFE ROUTER TESTING
# ============================================================

def recognize_command(
    command: str,
) -> dict:
    """
    Tests which handler recognizes a command WITHOUT
    actually executing the system action.

    This is useful for development.
    """

    cleaned = clean_command(command)

    if not cleaned:
        return {
            "recognized": False,
            "command": command,
            "cleaned": "",
            "handler": None,
        }

    # Specific recognition tests.

    tests = [
        ("context", handle_context_command),
        ("help", handle_help),
        ("website_browser", handle_website_on_browser),
        ("website", handle_website),
        ("application", handle_application),
        ("close", handle_close),
        ("folder", handle_folder),
        ("screenshot", handle_screenshot),
        ("audio", handle_audio),
        ("battery", handle_battery),
        ("datetime", handle_datetime),
        ("calculation", handle_calculation),
        ("current_app", handle_current_app),
        ("search", handle_search),
    ]

    for name, handler in tests:

        try:

            # We can't call handlers because some execute.
            # Instead use command-specific recognition rules.

            if name == "application":
                if re.match(
                    r"^(?:open|launch|start|run)\s+",
                    cleaned.lower(),
                ):
                    target = normalize_target(
                        re.sub(
                            r"^(?:open|launch|start|run)\s+",
                            "",
                            cleaned.lower(),
                        )
                    )

                    if target in APPLICATIONS:
                        return {
                            "recognized": True,
                            "command": command,
                            "cleaned": cleaned,
                            "handler": name,
                        }

            elif name == "website":
                if re.match(
                    r"^(?:open|launch|go to|visit)\s+",
                    cleaned.lower(),
                ):
                    target = normalize_target(
                        re.sub(
                            r"^(?:open|launch|go to|visit)\s+",
                            "",
                            cleaned.lower(),
                        )
                    )

                    if target in WEBSITES:
                        return {
                            "recognized": True,
                            "command": command,
                            "cleaned": cleaned,
                            "handler": name,
                        }

            elif name == "folder":
                target_match = re.match(
                    r"^(?:open|go to)\s+(.+?)(?:\s+folder)?$",
                    cleaned.lower(),
                )

                if target_match:

                    target = normalize_target(
                        target_match.group(1)
                    )

                    if target in FOLDERS:
                        return {
                            "recognized": True,
                            "command": command,
                            "cleaned": cleaned,
                            "handler": name,
                        }

            elif name == "screenshot":
                if any(
                    x in cleaned.lower()
                    for x in (
                        "take a screenshot",
                        "take screenshot",
                        "screenshot",
                        "capture my screen",
                        "capture the screen",
                    )
                ):
                    return {
                        "recognized": True,
                        "command": command,
                        "cleaned": cleaned,
                        "handler": name,
                    }

            elif name == "battery":
                if "battery" in cleaned.lower():
                    return {
                        "recognized": True,
                        "command": command,
                        "cleaned": cleaned,
                        "handler": name,
                    }

            elif name == "datetime":
                if any(
                    phrase in cleaned.lower()
                    for phrase in (
                        "what time is it",
                        "current time",
                        "what date is it",
                        "today's date",
                    )
                ):
                    return {
                        "recognized": True,
                        "command": command,
                        "cleaned": cleaned,
                        "handler": name,
                    }

            elif name == "calculation":
                if re.match(
                    r"^(?:calculate|compute)\s+",
                    cleaned.lower(),
                ):
                    return {
                        "recognized": True,
                        "command": command,
                        "cleaned": cleaned,
                        "handler": name,
                    }

            elif name == "search":
                if re.match(
                    r"^(?:search|google|look up|search for)\s+",
                    cleaned.lower(),
                ):
                    return {
                        "recognized": True,
                        "command": command,
                        "cleaned": cleaned,
                        "handler": name,
                    }

            elif name == "help":
                if cleaned.lower() in {
                    "help",
                    "what can you do",
                    "show commands",
                }:
                    return {
                        "recognized": True,
                        "command": command,
                        "cleaned": cleaned,
                        "handler": name,
                    }

            elif name == "context":
                if cleaned.lower() in {
                    "open it",
                    "launch it",
                    "close it",
                    "open that",
                    "open that website",
                }:
                    return {
                        "recognized": True,
                        "command": command,
                        "cleaned": cleaned,
                        "handler": name,
                    }

        except Exception:
            continue

    return {
        "recognized": False,
        "command": command,
        "cleaned": cleaned,
        "handler": None,
    }


# ============================================================
# SELF TEST
# ============================================================

def self_test() -> dict:

    test_commands = [

        "Hello Nova, open Calculator",

        "Hey Nova, open VS Code",

        "Open Safari",

        "Close Safari",

        "Open YouTube",

        "Open YouTube on Safari",

        "Open Google on Chrome",

        "Open WhatsApp",

        "Open Downloads",

        "Open Desktop",

        "Open Documents",

        "Take a screenshot",

        "Mute my Mac",

        "Unmute",

        "Set volume to 50",

        "Check my battery",

        "What time is it",

        "Calculate 25 * 8",

        "Search for Python tutorials",

        "What app is open",

        "Open it",

        "Close it",

        "What can you do",

        "Tell me a joke",
    ]

    results = []

    for command in test_commands:

        result = recognize_command(command)

        results.append(result)

    recognized = sum(
        1
        for result in results
        if result["recognized"]
    )

    return {
        "success": True,
        "total": len(results),
        "recognized": recognized,
        "not_recognized": len(results) - recognized,
        "tests": results,
    }


# ============================================================
# DEBUG CLI
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("NOVA ADVANCED TOOL ROUTER")
    print("=" * 70)
    print()

    print("Router state:")
    print(get_router_state())
    print()

    print("Running recognition self-test...")
    print()

    test = self_test()

    for item in test["tests"]:

        status = (
            "✓"
            if item["recognized"]
            else "✗"
        )

        print(
            f"{status} "
            f"{item['command']}"
            f" -> "
            f"{item['handler']}"
        )

    print()
    print(
        f"Recognized: "
        f"{test['recognized']}/"
        f"{test['total']}"
    )

    print()
    print("=" * 70)
    print("INTERACTIVE ROUTER")
    print("=" * 70)
    print()

    while True:

        try:

            command = input(
                "Command > "
            ).strip()

        except KeyboardInterrupt:

            print()
            break

        except EOFError:

            print()
            break

        if command.lower() in {
            "exit",
            "quit",
        }:

            break

        if command.lower() == "state":

            print(
                get_router_state()
            )
            print()
            continue

        if command.lower() == "self test":

            print(
                self_test()
            )
            print()
            continue

        result = route_command(
            command
        )

        print()
        print(result)
        print()