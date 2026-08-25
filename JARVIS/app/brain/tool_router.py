from __future__ import annotations

"""
============================================================
NOVA ADVANCED TOOL ROUTER
============================================================

Purpose
-------
This module converts natural-language commands into real
computer actions.

IMPORTANT ARCHITECTURE

    User
      |
      v
    NOVA UI
      |
      v
    TOOL ROUTER
      |
      +----> System action
      |
      +----> Browser action
      |
      +----> File/folder action
      |
      +----> Audio/system action
      |
      +----> Not a system command
                  |
                  v
                QWEN

The router executes deterministic computer commands BEFORE
the AI model gets a chance to answer them.

Examples
--------

    Hello Nova, open Calculator
    Open VS Code
    Launch WhatsApp
    Open YouTube
    Open YouTube on Safari
    Open Google on Chrome
    Open it
    Launch that
    Close Safari
    Open Downloads
    Open Desktop
    Take a screenshot
    Mute my Mac
    Unmute
    Set volume to 50
    Check battery
    What time is it?
    Calculate 25 * 8

============================================================
"""

import os
import re
import subprocess
from typing import Any, Optional


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
)


# ============================================================
# USER / NOVA CONFIGURATION
# ============================================================

USER_NAME = "Saksham"

NOVA_NAME = "NOVA"


# ============================================================
# HOME DIRECTORY
# ============================================================

HOME = os.path.expanduser("~")


# ============================================================
# APPLICATION ALIASES
# ============================================================

APPLICATIONS = {

    # --------------------------------------------------------
    # Apple
    # --------------------------------------------------------

    "safari":
        "Safari",

    "finder":
        "Finder",

    "terminal":
        "Terminal",

    "calculator":
        "Calculator",

    "notes":
        "Notes",

    "calendar":
        "Calendar",

    "mail":
        "Mail",

    "messages":
        "Messages",

    "facetime":
        "FaceTime",

    "photos":
        "Photos",

    "preview":
        "Preview",

    "music":
        "Music",

    "quicktime":
        "QuickTime Player",

    "system settings":
        "System Settings",

    "settings":
        "System Settings",


    # --------------------------------------------------------
    # Browsers
    # --------------------------------------------------------

    "chrome":
        "Google Chrome",

    "google chrome":
        "Google Chrome",

    "firefox":
        "Firefox",

    "edge":
        "Microsoft Edge",

    "microsoft edge":
        "Microsoft Edge",


    # --------------------------------------------------------
    # Development
    # --------------------------------------------------------

    "vs code":
        "Visual Studio Code",

    "vscode":
        "Visual Studio Code",

    "visual studio code":
        "Visual Studio Code",

    "code":
        "Visual Studio Code",

    "cursor":
        "Cursor",

    "xcode":
        "Xcode",

    "pycharm":
        "PyCharm",

    "android studio":
        "Android Studio",


    # --------------------------------------------------------
    # Communication
    # --------------------------------------------------------

    "whatsapp":
        "WhatsApp",

    "whatsapp desktop":
        "WhatsApp",

    "discord":
        "Discord",

    "telegram":
        "Telegram",

    "slack":
        "Slack",

    "zoom":
        "zoom.us",

    "microsoft teams":
        "Microsoft Teams",

    "teams":
        "Microsoft Teams",


    # --------------------------------------------------------
    # Entertainment
    # --------------------------------------------------------

    "spotify":
        "Spotify",

    "netflix":
        "Netflix",

    "vlc":
        "VLC",

    "steam":
        "Steam",


    # --------------------------------------------------------
    # Microsoft
    # --------------------------------------------------------

    "word":
        "Microsoft Word",

    "microsoft word":
        "Microsoft Word",

    "excel":
        "Microsoft Excel",

    "microsoft excel":
        "Microsoft Excel",

    "powerpoint":
        "Microsoft PowerPoint",

    "microsoft powerpoint":
        "Microsoft PowerPoint",


    # --------------------------------------------------------
    # Productivity
    # --------------------------------------------------------

    "notion":
        "Notion",

    "obsidian":
        "Obsidian",

    "figma":
        "Figma",

}


# ============================================================
# WEBSITE ALIASES
# ============================================================

WEBSITES = {

    "youtube":
        "https://youtube.com",

    "youtube.com":
        "https://youtube.com",

    "google":
        "https://google.com",

    "google.com":
        "https://google.com",

    "gmail":
        "https://mail.google.com",

    "gmail.com":
        "https://mail.google.com",

    "whatsapp web":
        "https://web.whatsapp.com",

    "github":
        "https://github.com",

    "github.com":
        "https://github.com",

    "chatgpt":
        "https://chatgpt.com",

    "instagram":
        "https://instagram.com",

    "facebook":
        "https://facebook.com",

    "linkedin":
        "https://linkedin.com",

    "reddit":
        "https://reddit.com",

    "twitter":
        "https://x.com",

    "x":
        "https://x.com",

    "amazon":
        "https://amazon.in",

    "amazon india":
        "https://amazon.in",

    "netflix":
        "https://netflix.com",

    "spotify web":
        "https://open.spotify.com",

    "stackoverflow":
        "https://stackoverflow.com",

    "wikipedia":
        "https://wikipedia.org",

}


# ============================================================
# FOLDER ALIASES
# ============================================================

FOLDERS = {

    "home":
        HOME,

    "home folder":
        HOME,

    "desktop":
        os.path.join(
            HOME,
            "Desktop",
        ),

    "desktop folder":
        os.path.join(
            HOME,
            "Desktop",
        ),

    "downloads":
        os.path.join(
            HOME,
            "Downloads",
        ),

    "download":
        os.path.join(
            HOME,
            "Downloads",
        ),

    "documents":
        os.path.join(
            HOME,
            "Documents",
        ),

    "documents folder":
        os.path.join(
            HOME,
            "Documents",
        ),

    "pictures":
        os.path.join(
            HOME,
            "Pictures",
        ),

    "photos folder":
        os.path.join(
            HOME,
            "Pictures",
        ),

    "movies":
        os.path.join(
            HOME,
            "Movies",
        ),

    "music":
        os.path.join(
            HOME,
            "Music",
        ),

}


# ============================================================
# BROWSER ALIASES
# ============================================================

BROWSERS = {

    "safari":
        "Safari",

    "chrome":
        "Google Chrome",

    "google chrome":
        "Google Chrome",

    "firefox":
        "Firefox",

    "edge":
        "Microsoft Edge",

    "microsoft edge":
        "Microsoft Edge",

}


# ============================================================
# LAST COMMAND CONTEXT
# ============================================================

_last_application: Optional[str] = None

_last_website: Optional[str] = None

_last_folder: Optional[str] = None


# ============================================================
# CONTEXT FUNCTIONS
# ============================================================

def remember_application(
    application: str,
) -> None:

    global _last_application

    _last_application = application


def remember_website(
    url: str,
) -> None:

    global _last_website

    _last_website = url


def remember_folder(
    folder: str,
) -> None:

    global _last_folder

    _last_folder = folder


def get_last_application() -> Optional[str]:

    return _last_application


def get_last_website() -> Optional[str]:

    return _last_website


def get_last_folder() -> Optional[str]:

    return _last_folder


# ============================================================
# RESULT HELPERS
# ============================================================

def handled(
    message: str,
    data: Any = None,
) -> dict:

    return {
        "handled": True,
        "success": True,
        "message": message,
        "data": data,
    }


def failed(
    message: str,
    data: Any = None,
) -> dict:

    return {
        "handled": True,
        "success": False,
        "message": message,
        "data": data,
    }


def not_handled() -> dict:

    return {
        "handled": False,
        "success": False,
        "message": "",
        "data": None,
    }


# ============================================================
# COMMAND CLEANING
# ============================================================

def clean_command(
    text: str,
) -> str:

    """
    Removes NOVA wake words and conversational noise.

    Examples:

        Hello Nova, Open Calculator
        Hey Nova open Safari
        Nova: open YouTube
        Hi Nova, launch VS Code
    """

    if not text:

        return ""

    text = str(text).strip()

    # --------------------------------------------------------
    # Repeated wake-word removal
    # --------------------------------------------------------

    wake_words = (
        "hello nova",
        "hey nova",
        "hi nova",
        "nova",
    )

    changed = True

    while changed:

        changed = False

        lower = text.lower().strip()

        for wake_word in wake_words:

            if lower.startswith(
                wake_word
            ):

                text = text[
                    len(wake_word):
                ].strip()

                # Remove punctuation after wake word.

                while (
                    text
                    and text[0]
                    in ",:;.!?-"
                ):

                    text = text[
                        1:
                    ].strip()

                changed = True

                break

    # --------------------------------------------------------
    # Remove common polite endings
    # --------------------------------------------------------

    text = re.sub(
        r"\s+(please|for me|thanks|thank you)\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


# ============================================================
# NORMALIZE TARGET
# ============================================================

def normalize_target(
    target: str,
) -> str:

    target = target.lower().strip()

    target = target.rstrip(
        ".,!?;:"
    )

    target = re.sub(
        r"\s+",
        " ",
        target,
    )

    return target


# ============================================================
# URL RESOLUTION
# ============================================================

def resolve_website(
    target: str,
) -> Optional[str]:

    target = normalize_target(
        target
    )

    if target in WEBSITES:

        return WEBSITES[target]

    if target.startswith(
        "https://"
    ):

        return target

    if target.startswith(
        "http://"
    ):

        return target

    # Domain typed directly.

    if re.match(
        r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        target,
    ):

        return (
            "https://"
            + target
        )

    return None


# ============================================================
# APPLICATION RESOLUTION
# ============================================================

def resolve_application(
    target: str,
) -> Optional[str]:

    target = normalize_target(
        target
    )

    if target in APPLICATIONS:

        return APPLICATIONS[target]

    return None


# ============================================================
# BROWSER RESOLUTION
# ============================================================

def resolve_browser(
    target: str,
) -> Optional[str]:

    target = normalize_target(
        target
    )

    return BROWSERS.get(
        target
    )


# ============================================================
# OPEN WEBSITE IN SPECIFIC BROWSER
# ============================================================

def open_url_in_browser(
    url: str,
    browser: Optional[str] = None,
) -> dict:

    """
    Opens a URL in a specific macOS browser.

    If browser is None, the default browser is used.
    """

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
            "success":
                result.returncode == 0,

            "url":
                url,

            "browser":
                browser,

            "error":
                result.stderr.strip(),
        }

    except Exception as error:

        return {
            "success": False,
            "url": url,
            "browser": browser,
            "error": str(error),
        }


# ============================================================
# OPEN "WEBSITE ON BROWSER"
# ============================================================

def handle_website_on_browser(
    command: str,
) -> dict:

    lower = command.lower().strip()

    patterns = [

        r"(?:open|launch|go to|visit)\s+(.+?)\s+on\s+(.+)$",

        r"(?:open|launch|go to|visit)\s+(.+?)\s+using\s+(.+)$",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            lower,
        )

        if not match:

            continue

        website_target = (
            match.group(1)
            .strip()
        )

        browser_target = (
            match.group(2)
            .strip()
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

        # ----------------------------------------------------
        # Open browser + URL
        # ----------------------------------------------------

        result = open_url_in_browser(
            url,
            browser,
        )

        if not result.get(
            "success"
        ):

            return failed(
                f"I couldn't open "
                f"{website_target} in "
                f"{browser}.",
                result,
            )

        remember_application(
            browser
        )

        remember_website(
            url
        )

        return handled(
            f"Done. I opened "
            f"{website_target.title()} "
            f"in {browser}.",
            result,
        )

    return not_handled()


# ============================================================
# OPEN WEBSITE
# ============================================================

def handle_website(
    command: str,
) -> dict:

    lower = command.lower().strip()

    # --------------------------------------------------------
    # Browser-specific command first
    # --------------------------------------------------------

    result = handle_website_on_browser(
        command
    )

    if result.get(
        "handled"
    ):

        return result

    # --------------------------------------------------------
    # Normal open / visit command
    # --------------------------------------------------------

    match = re.search(
        r"^(?:open|launch|go to|visit)\s+(.+)$",
        lower,
    )

    if not match:

        return not_handled()

    target = match.group(
        1
    ).strip()

    target = normalize_target(
        target
    )

    # --------------------------------------------------------
    # Don't treat applications as websites
    # --------------------------------------------------------

    if target in APPLICATIONS:

        return not_handled()

    # --------------------------------------------------------
    # Resolve website
    # --------------------------------------------------------

    url = resolve_website(
        target
    )

    if not url:

        return not_handled()

    try:

        result = open_website_new_tab(
            url
        )

    except Exception:

        result = open_url_in_browser(
            url
        )

    if result.get(
        "success"
    ):

        remember_website(
            url
        )

        return handled(
            f"Done. I opened "
            f"{target.title()}.",
            result,
        )

    return failed(
        f"I couldn't open "
        f"{target}.",
        result,
    )


# ============================================================
# OPEN APPLICATION
# ============================================================

def handle_application(
    command: str,
) -> dict:

    lower = command.lower().strip()

    # --------------------------------------------------------
    # CONTEXT COMMANDS
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

        if not _last_application:

            return failed(
                "I don't know which application "
                "you mean yet."
            )

        result = open_application(
            _last_application
        )

        if result.get(
            "success"
        ):

            return handled(
                f"Done. "
                f"{_last_application} "
                f"is open.",
                result,
            )

        return failed(
            f"I couldn't open "
            f"{_last_application}.",
            result,
        )

    # --------------------------------------------------------
    # Standard launch command
    # --------------------------------------------------------

    match = re.search(
        r"^(?:open|launch|start|run)\s+(.+)$",
        lower,
    )

    if not match:

        return not_handled()

    target = match.group(
        1
    ).strip()

    target = normalize_target(
        target
    )

    # --------------------------------------------------------
    # Remove words that shouldn't affect app matching
    # --------------------------------------------------------

    target = re.sub(
        r"\s+(application|app)$",
        "",
        target,
    ).strip()

    application = resolve_application(
        target
    )

    if not application:

        return not_handled()

    # --------------------------------------------------------
    # Launch
    # --------------------------------------------------------

    try:

        result = open_application(
            application
        )

    except Exception as error:

        return failed(
            f"I couldn't open "
            f"{application}.",
            {
                "error": str(error),
            },
        )

    if result.get(
        "success"
    ):

        remember_application(
            application
        )

        return handled(
            f"Done. "
            f"{application} "
            f"is open.",
            result,
        )

    # --------------------------------------------------------
    # WhatsApp fallback
    # --------------------------------------------------------

    if application == "WhatsApp":

        try:

            fallback = open_url_in_browser(
                "https://web.whatsapp.com"
            )

            if fallback.get(
                "success"
            ):

                remember_application(
                    application
                )

                remember_website(
                    "https://web.whatsapp.com"
                )

                return handled(
                    "WhatsApp Desktop isn't "
                    "available, so I opened "
                    "WhatsApp Web instead.",
                    fallback,
                )

        except Exception:

            pass

    return failed(
        f"I couldn't open "
        f"{application}.",
        result,
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

    # --------------------------------------------------------
    # "close it"
    # --------------------------------------------------------

    if target in {
        "it",
        "that",
        "the app",
        "the application",
    }:

        if not _last_application:

            return failed(
                "I don't know which application "
                "you want me to close."
            )

        application = _last_application

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
            f"I couldn't close "
            f"{application}.",
            {
                "error": str(error),
            },
        )

    if result.get(
        "success"
    ):

        return handled(
            f"Done. I closed "
            f"{application}.",
            result,
        )

    return failed(
        f"I couldn't close "
        f"{application}.",
        result,
    )


# ============================================================
# FOLDER HANDLER
# ============================================================

def handle_folder(
    command: str,
) -> dict:

    lower = command.lower().strip()

    # --------------------------------------------------------
    # Open folder
    # --------------------------------------------------------

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

            result = open_folder(
                path
            )

        except Exception as error:

            return failed(
                f"I couldn't open "
                f"the {target} folder.",
                {
                    "error": str(error),
                },
            )

        if result.get(
            "success"
        ):

            remember_folder(
                path
            )

            return handled(
                f"Done. I opened "
                f"the {target} folder.",
                result,
            )

        return failed(
            f"I couldn't open "
            f"the {target} folder.",
            result,
        )

    return not_handled()


# ============================================================
# SCREENSHOT
# ============================================================

def handle_screenshot(
    command: str,
) -> dict:

    lower = command.lower()

    phrases = [

        "take a screenshot",

        "take screenshot",

        "screenshot",

        "capture my screen",

        "capture the screen",

        "capture screen",

        "take a screen capture",

    ]

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
            {
                "error": str(error),
            },
        )

    if result.get(
        "success"
    ):

        return handled(
            "Done. I took a screenshot.",
            result,
        )

    return failed(
        "I couldn't take a screenshot.",
        result,
    )


# ============================================================
# AUDIO CONTROL
# ============================================================

def handle_audio(
    command: str,
) -> dict:

    lower = command.lower().strip()

    # --------------------------------------------------------
    # MUTE
    # --------------------------------------------------------

    if (
        "mute" in lower
        and "unmute" not in lower
    ):

        try:

            result = mute_audio()

        except Exception as error:

            return failed(
                "I couldn't mute the Mac.",
                {
                    "error": str(error),
                },
            )

        if result.get(
            "success"
        ):

            return handled(
                "Done. Your Mac is muted.",
                result,
            )

        return failed(
            "I couldn't mute the Mac.",
            result,
        )

    # --------------------------------------------------------
    # UNMUTE
    # --------------------------------------------------------

    if "unmute" in lower:

        try:

            result = unmute_audio()

        except Exception as error:

            return failed(
                "I couldn't unmute the Mac.",
                {
                    "error": str(error),
                },
            )

        if result.get(
            "success"
        ):

            return handled(
                "Done. Your Mac is unmuted.",
                result,
            )

        return failed(
            "I couldn't unmute the Mac.",
            result,
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

        level = int(
            match.group(1)
        )

        if level < 0 or level > 100:

            return failed(
                "Volume must be between 0 and 100."
            )

        try:

            result = set_volume(
                level
            )

        except Exception as error:

            return failed(
                "I couldn't change the volume.",
                {
                    "error": str(error),
                },
            )

        if result.get(
            "success"
        ):

            return handled(
                f"Done. Volume is now "
                f"{level}%.",
                result,
            )

        return failed(
            "I couldn't change the volume.",
            result,
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
            {
                "error": str(error),
            },
        )

    if not result.get(
        "success"
    ):

        return failed(
            "I couldn't read the battery.",
            result,
        )

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

        return handled(
            f"Your battery is at "
            f"{percentage}% and is "
            f"{state}.",
            result,
        )

    return handled(
        "I retrieved your battery status.",
        result,
    )


# ============================================================
# TIME / DATE
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
            {
                "error": str(error),
            },
        )

    formatted = result.get(
        "formatted"
    )

    if formatted:

        return handled(
            f"It is {formatted}.",
            result,
        )

    return handled(
        "I retrieved the current date and time.",
        result,
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

        r"^what is\s+([0-9][0-9\s+\-*/().%^]*)$",

    ]

    expression = None

    for pattern in patterns:

        match = re.search(
            pattern,
            lower,
        )

        if match:

            expression = match.group(
                1
            ).strip()

            break

    if not expression:

        return not_handled()

    # --------------------------------------------------------
    # Safety filter
    # --------------------------------------------------------

    if not re.fullmatch(
        r"[0-9\s+\-*/().%^]+",
        expression,
    ):

        return not_handled()

    try:

        result = calculate(
            expression
        )

    except Exception:

        return not_handled()

    if not result.get(
        "success"
    ):

        return failed(
            "I couldn't calculate that.",
            result,
        )

    return handled(
        f"The answer is "
        f"{result.get('result')}.",
        result,
    )


# ============================================================
# SEARCH WEB
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

            query = match.group(
                1
            ).strip()

            break

    if not query:

        return not_handled()

    # --------------------------------------------------------
    # Google search URL
    # --------------------------------------------------------

    import urllib.parse

    encoded = urllib.parse.quote_plus(
        query
    )

    url = (
        "https://www.google.com/search?q="
        + encoded
    )

    result = open_website_new_tab(
        url
    )

    if result.get(
        "success"
    ):

        remember_website(
            url
        )

        return handled(
            f"Done. I searched Google "
            f"for {query}.",
            result,
        )

    return failed(
        "I couldn't perform the web search.",
        result,
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
            {
                "error": str(error),
            },
        )

    if not result.get(
        "success"
    ):

        return failed(
            "I couldn't determine the active application.",
            result,
        )

    application = result.get(
        "application"
    )

    return handled(
        f"The active application is "
        f"{application}.",
        result,
    )


# ============================================================
# GENERIC CONTEXT COMMANDS
# ============================================================

def handle_context_command(
    command: str,
) -> dict:

    """
    Handles commands that refer to the previous action.
    """

    lower = command.lower().strip()

    # --------------------------------------------------------
    # Reopen last app
    # --------------------------------------------------------

    if lower in {
        "open it",
        "launch it",
        "start it",
        "run it",
        "open that",
        "launch that",
        "start that",
    }:

        if _last_application:

            result = open_application(
                _last_application
            )

            if result.get(
                "success"
            ):

                return handled(
                    f"Done. "
                    f"{_last_application} "
                    f"is open.",
                    result,
                )

            return failed(
                f"I couldn't open "
                f"{_last_application}.",
                result,
            )

        return failed(
            "I don't have a previous application "
            "to open yet."
        )

    # --------------------------------------------------------
    # Reopen last website
    # --------------------------------------------------------

    if lower in {
        "open that website",
        "open the website",
        "open the site",
        "open it in the browser",
    }:

        if _last_website:

            result = open_website_new_tab(
                _last_website
            )

            if result.get(
                "success"
            ):

                return handled(
                    "Done. I reopened the website.",
                    result,
                )

            return failed(
                "I couldn't reopen the website.",
                result,
            )

        return failed(
            "I don't have a previous website yet."
        )

    # --------------------------------------------------------
    # Close previous app
    # --------------------------------------------------------

    if lower in {
        "close it",
        "close that",
        "close the app",
        "close the application",
    }:

        if not _last_application:

            return failed(
                "I don't know which application "
                "you mean."
            )

        result = close_application(
            _last_application
        )

        if result.get(
            "success"
        ):

            return handled(
                f"Done. I closed "
                f"{_last_application}.",
                result,
            )

        return failed(
            f"I couldn't close "
            f"{_last_application}.",
            result,
        )

    return not_handled()


# ============================================================
# MAIN ROUTER
# ============================================================

def route_command(
    user_input: str,
) -> dict:

    """
    Main entry point.

    Returns:

        handled=True
            The router recognized and attempted
            a computer/system action.

        handled=False
            This is not a deterministic system command.
            Send it to Qwen.
    """

    if not user_input:

        return not_handled()

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    command = clean_command(
        user_input
    )

    if not command:

        return not_handled()

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print(
        f"[ROUTER] {user_input!r}"
        f" -> {command!r}"
    )

    # ========================================================
    # HANDLER ORDER
    # ========================================================

    handlers = [

        # Context must happen early.
        handle_context_command,

        # Browser-specific commands.
        handle_website_on_browser,

        # Website commands.
        handle_website,

        # Applications.
        handle_application,

        # Closing.
        handle_close,

        # Folders.
        handle_folder,

        # Screenshots.
        handle_screenshot,

        # Audio.
        handle_audio,

        # Battery.
        handle_battery,

        # Date/time.
        handle_datetime,

        # Calculator.
        handle_calculation,

        # Web search.
        handle_search,

        # Active app.
        handle_current_app,

    ]

    for handler in handlers:

        try:

            result = handler(
                command
            )

            if result.get(
                "handled"
            ):

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
                    "handler":
                        handler.__name__,

                    "error":
                        str(error),
                },
            )

    # ========================================================
    # NOT A SYSTEM COMMAND
    # ========================================================

    print(
        "[ROUTER] No deterministic "
        "system command detected."
    )

    return not_handled()


# ============================================================
# ROUTER STATE
# ============================================================

def get_router_state() -> dict:

    return {

        "last_application":
            _last_application,

        "last_website":
            _last_website,

        "last_folder":
            _last_folder,

    }


def reset_router_state() -> None:

    global _last_application
    global _last_website
    global _last_folder

    _last_application = None
    _last_website = None
    _last_folder = None


# ============================================================
# SELF TEST
# ============================================================

def self_test() -> dict:

    """
    Non-destructive router test.

    IMPORTANT:
    This only tests recognition. It does NOT actually launch
    applications because that would make a self-test disruptive.
    """

    test_commands = [

        "Hello Nova, open Calculator",

        "Hey Nova, open VS Code",

        "Open YouTube",

        "Open YouTube on Safari",

        "Open Google on Chrome",

        "Open WhatsApp",

        "Open Downloads",

        "Take a screenshot",

        "Mute my Mac",

        "Set volume to 50",

        "Check my battery",

        "What time is it",

        "Calculate 25 * 8",

        "Search for Python tutorials",

        "open it",

        "close it",

    ]

    results = []

    for command in test_commands:

        cleaned = clean_command(
            command
        )

        results.append(
            {
                "input":
                    command,

                "cleaned":
                    cleaned,

                "recognized":
                    bool(cleaned),
            }
        )

    return {
        "success": True,
        "tests": results,
    }


# ============================================================
# DEBUG CLI
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("NOVA TOOL ROUTER TEST")
    print("=" * 60)
    print()

    print(
        "Router state:"
    )

    print(
        get_router_state()
    )

    print()

    while True:

        try:

            command = input(
                "Command > "
            ).strip()

        except KeyboardInterrupt:

            break

        except EOFError:

            break

        if command.lower() in {
            "exit",
            "quit",
        }:

            break

        result = route_command(
            command
        )

        print()

        print(
            result
        )

        print()
