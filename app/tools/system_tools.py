from __future__ import annotations

"""
============================================================
NOVA ADVANCED SYSTEM TOOLS
============================================================

macOS system-control layer for NOVA.

Capabilities
------------
Applications
    • Open applications
    • Close applications
    • Activate applications
    • Check installed applications
    • List installed applications
    • Resolve application aliases

Web
    • Open websites
    • Open new Safari tabs
    • Website shortcuts

Files
    • Open folders
    • Open Home/Desktop/Documents/Downloads
    • Create text files
    • Read text files
    • Write text files

System
    • System information
    • Battery
    • Date/time
    • Active application
    • Volume
    • Mute/unmute
    • Screenshot
    • Lock display

Utilities
    • Clipboard read/write
    • Calculator
    • Shell commands
    • Tool status
    • Self-test

Designed for
------------
macOS
Python 3.12+
Apple Silicon / Intel
============================================================
"""

import ast
import datetime as dt
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

SYSTEM = platform.system()
HOME = Path.home()

APPLICATION_DIRECTORIES = [
    Path("/Applications"),
    Path("/System/Applications"),
    HOME / "Applications",
]

COMMON_FOLDERS = {
    "home": HOME,
    "desktop": HOME / "Desktop",
    "documents": HOME / "Documents",
    "downloads": HOME / "Downloads",
    "pictures": HOME / "Pictures",
    "movies": HOME / "Movies",
    "music": HOME / "Music",
}


# ============================================================
# APPLICATION ALIASES
# ============================================================

APPLICATION_ALIASES: dict[str, str] = {

    # Apple
    "safari": "Safari",
    "browser": "Safari",
    "finder": "Finder",
    "file manager": "Finder",
    "terminal": "Terminal",
    "settings": "System Settings",
    "system settings": "System Settings",
    "messages": "Messages",
    "imessage": "Messages",
    "facetime": "FaceTime",
    "mail": "Mail",
    "apple mail": "Mail",
    "calendar": "Calendar",
    "notes": "Notes",
    "reminders": "Reminders",
    "photos": "Photos",
    "music": "Music",
    "apple music": "Music",
    "maps": "Maps",
    "calculator": "Calculator",
    "calc": "Calculator",
    "preview": "Preview",
    "activity monitor": "Activity Monitor",
    "disk utility": "Disk Utility",
    "textedit": "TextEdit",
    "text edit": "TextEdit",
    "app store": "App Store",
    "system information": "System Information",

    # Browsers
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "firefox": "Firefox",
    "mozilla": "Firefox",
    "arc": "Arc",
    "brave": "Brave Browser",
    "brave browser": "Brave Browser",
    "edge": "Microsoft Edge",
    "microsoft edge": "Microsoft Edge",

    # Development
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "vs-code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "visual studio": "Visual Studio",
    "xcode": "Xcode",
    "pycharm": "PyCharm",
    "intellij": "IntelliJ IDEA",
    "intellij idea": "IntelliJ IDEA",
    "webstorm": "WebStorm",
    "sublime": "Sublime Text",
    "sublime text": "Sublime Text",
    "cursor": "Cursor",
    "android studio": "Android Studio",
    "postman": "Postman",
    "docker": "Docker",
    "github desktop": "GitHub Desktop",

    # Communication
    "whatsapp": "WhatsApp",
    "whatsapp desktop": "WhatsApp",
    "wa": "WhatsApp",
    "telegram": "Telegram",
    "telegram desktop": "Telegram",
    "discord": "Discord",
    "slack": "Slack",
    "zoom": "zoom.us",
    "zoom meeting": "zoom.us",
    "teams": "Microsoft Teams",
    "microsoft teams": "Microsoft Teams",
    "skype": "Skype",

    # Microsoft
    "word": "Microsoft Word",
    "microsoft word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "microsoft excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "microsoft powerpoint": "Microsoft PowerPoint",
    "outlook": "Microsoft Outlook",
    "onenote": "Microsoft OneNote",

    # Media
    "spotify": "Spotify",
    "vlc": "VLC",
    "vlc player": "VLC",
    "obs": "OBS",
    "obs studio": "OBS",
    "steam": "Steam",

    # Creative
    "photoshop": "Adobe Photoshop",
    "adobe photoshop": "Adobe Photoshop",
    "premiere": "Adobe Premiere Pro",
    "premiere pro": "Adobe Premiere Pro",
    "adobe premiere": "Adobe Premiere Pro",
    "illustrator": "Adobe Illustrator",
    "adobe illustrator": "Adobe Illustrator",
    "lightroom": "Adobe Lightroom",

    # Productivity
    "notion": "Notion",
    "evernote": "Evernote",
    "todoist": "Todoist",
    "dropbox": "Dropbox",
    "google drive": "Google Drive",
}


# ============================================================
# WEBSITE SHORTCUTS
# ============================================================

WEBSITE_SHORTCUTS: dict[str, str] = {
    "youtube": "https://youtube.com",
    "youtube.com": "https://youtube.com",
    "google": "https://google.com",
    "gmail": "https://mail.google.com",
    "whatsapp web": "https://web.whatsapp.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "instagram": "https://instagram.com",
    "facebook": "https://facebook.com",
    "linkedin": "https://linkedin.com",
    "reddit": "https://reddit.com",
    "x": "https://x.com",
    "twitter": "https://x.com",
    "amazon": "https://amazon.in",
    "netflix": "https://netflix.com",
    "spotify web": "https://open.spotify.com",
}


# ============================================================
# RESULT HELPER
# ============================================================

def _result(success: bool, **kwargs: Any) -> dict[str, Any]:
    return {
        "success": success,
        **kwargs,
    }


# ============================================================
# SUBPROCESS HELPER
# ============================================================

def _run(
    command: list[str],
    timeout: float = 15,
) -> subprocess.CompletedProcess[str]:

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_name(application: str) -> str:

    if not application:
        return ""

    cleaned = (
        str(application)
        .strip()
        .strip("\"'")
        .lower()
    )

    return APPLICATION_ALIASES.get(
        cleaned,
        str(application).strip(),
    )


# ============================================================
# APPLICATION DIRECTORIES
# ============================================================

def _application_directories() -> list[Path]:

    return [
        directory
        for directory in APPLICATION_DIRECTORIES
        if directory.exists()
    ]


# ============================================================
# FIND APPLICATION
# ============================================================

def _find_application(
    application: str,
) -> str | None:

    if not application:
        return None

    target = application.strip().lower()

    if target.endswith(".app"):
        target = target[:-4]

    # Exact path
    possible_path = Path(application).expanduser()

    if possible_path.exists():
        return str(possible_path)

    # Exact match
    for directory in _application_directories():

        try:

            for item in directory.iterdir():

                if not item.name.lower().endswith(".app"):
                    continue

                if item.stem.lower() == target:
                    return str(item)

        except (PermissionError, OSError):
            continue

    # Partial match
    for directory in _application_directories():

        try:

            for item in directory.iterdir():

                if not item.name.lower().endswith(".app"):
                    continue

                app_name = item.stem.lower()

                if (
                    target in app_name
                    or app_name in target
                ):
                    return str(item)

        except (PermissionError, OSError):
            continue

    return None


# ============================================================
# SYSTEM INFORMATION
# ============================================================

def get_system_info() -> dict:

    try:

        return _result(
            True,
            operating_system=SYSTEM,
            macos_version=platform.mac_ver()[0],
            processor=platform.machine(),
            hostname=platform.node(),
            user=os.environ.get("USER", "unknown"),
            python_version=platform.python_version(),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# APPLICATIONS
# ============================================================

def get_installed_applications() -> dict:

    applications: set[str] = set()

    for directory in _application_directories():

        try:

            for item in directory.iterdir():

                if item.name.endswith(".app"):
                    applications.add(item.stem)

        except (PermissionError, OSError):
            continue

    result = sorted(
        applications,
        key=str.lower,
    )

    return _result(
        True,
        count=len(result),
        applications=result,
    )


def is_application_installed(
    application: str,
) -> dict:

    resolved = _normalize_name(application)

    path = _find_application(resolved)

    return _result(
        path is not None,
        requested=application,
        application=resolved,
        installed=path is not None,
        path=path,
    )


# ============================================================
# OPEN APPLICATION
# ============================================================

def open_application(
    application: str,
) -> dict:

    if not application:

        return _result(
            False,
            error="No application specified.",
        )

    requested = str(application).strip()

    resolved = _normalize_name(requested)

    # --------------------------------------------------------
    # Launch through LaunchServices
    # --------------------------------------------------------

    try:

        result = _run(
            [
                "open",
                "-a",
                resolved,
            ],
            timeout=15,
        )

        if result.returncode == 0:

            # Try activation
            script = (
                f'tell application "{resolved}" '
                'to activate'
            )

            activation = _run(
                [
                    "osascript",
                    "-e",
                    script,
                ],
                timeout=10,
            )

            if activation.returncode == 0:

                return _result(
                    True,
                    application=resolved,
                    activated=True,
                    message=(
                        f"Opened and activated {resolved}."
                    ),
                )

            return _result(
                True,
                application=resolved,
                activated=False,
                message=(
                    f"Opened {resolved}."
                ),
            )

    except Exception:
        pass

    # --------------------------------------------------------
    # Manual application discovery
    # --------------------------------------------------------

    path = _find_application(resolved)

    if not path:

        return _result(
            False,
            application=resolved,
            error=(
                f"Unable to find '{resolved}' "
                "on this Mac."
            ),
        )

    try:

        result = _run(
            [
                "open",
                path,
            ]
        )

        if result.returncode == 0:

            return _result(
                True,
                application=resolved,
                path=path,
                message=f"Opened {resolved}.",
            )

        return _result(
            False,
            application=resolved,
            path=path,
            error=(
                result.stderr.strip()
                or "macOS could not open the application."
            ),
        )

    except Exception as error:

        return _result(
            False,
            application=resolved,
            error=str(error),
        )


# ============================================================
# ACTIVATE APPLICATION
# ============================================================

def activate_application(
    application: str,
) -> dict:

    if not application:

        return _result(
            False,
            error="No application specified.",
        )

    resolved = _normalize_name(application)

    script = (
        f'tell application "{resolved}" '
        "to activate"
    )

    try:

        result = _run(
            [
                "osascript",
                "-e",
                script,
            ]
        )

        return _result(
            result.returncode == 0,
            application=resolved,
            message=(
                f"Activated {resolved}."
                if result.returncode == 0
                else "Unable to activate application."
            ),
            error=(
                result.stderr.strip()
                if result.returncode != 0
                else None
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# CLOSE APPLICATION
# ============================================================

def close_application(
    application: str,
) -> dict:

    if not application:

        return _result(
            False,
            error="No application specified.",
        )

    resolved = _normalize_name(application)

    script = (
        f'tell application "{resolved}" '
        "to quit"
    )

    try:

        result = _run(
            [
                "osascript",
                "-e",
                script,
            ]
        )

        return _result(
            result.returncode == 0,
            application=resolved,
            message=(
                f"Closed {resolved}."
                if result.returncode == 0
                else f"Could not close {resolved}."
            ),
            error=(
                result.stderr.strip()
                if result.returncode != 0
                else None
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# OPEN WEBSITE
# ============================================================

def open_website(
    url: str,
) -> dict:

    if not url:

        return _result(
            False,
            error="No URL provided.",
        )

    url = str(url).strip()

    if not re.match(
        r"^https?://",
        url,
        re.IGNORECASE,
    ):
        url = "https://" + url

    try:

        result = _run(
            [
                "open",
                url,
            ]
        )

        return _result(
            result.returncode == 0,
            url=url,
            message=(
                f"Opened {url}."
                if result.returncode == 0
                else "Unable to open website."
            ),
            error=(
                result.stderr.strip()
                if result.returncode != 0
                else None
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# NEW SAFARI TAB
# ============================================================

def open_website_new_tab(
    url: str,
) -> dict:

    if not url:

        return _result(
            False,
            error="No URL provided.",
        )

    url = str(url).strip()

    if not re.match(
        r"^https?://",
        url,
        re.IGNORECASE,
    ):
        url = "https://" + url

    # Escape quotes for AppleScript
    safe_url = url.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
tell application "Safari"
    activate

    if (count of windows) = 0 then
        make new document with properties {{URL:"{safe_url}"}}
    else
        tell window 1
            make new tab with properties {{URL:"{safe_url}"}}
        end tell
    end if
end tell
'''

    try:

        result = _run(
            [
                "osascript",
                "-e",
                script,
            ]
        )

        if result.returncode == 0:

            return _result(
                True,
                url=url,
                message=(
                    f"Opened {url} in a new Safari tab."
                ),
            )

        return open_website(url)

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# WEBSITE SHORTCUT
# ============================================================

def open_shortcut(
    name: str,
) -> dict:

    if not name:

        return _result(
            False,
            error="No website shortcut specified.",
        )

    key = str(name).strip().lower()

    url = WEBSITE_SHORTCUTS.get(key)

    if not url:

        return _result(
            False,
            error=(
                f"No website shortcut exists "
                f"for '{name}'."
            ),
        )

    return open_website(url)


# ============================================================
# FOLDERS
# ============================================================

def open_folder(
    folder: str,
) -> dict:

    if not folder:

        return _result(
            False,
            error="No folder specified.",
        )

    key = str(folder).strip().lower()

    path = COMMON_FOLDERS.get(key)

    if path is None:

        path = Path(folder).expanduser()

    if not path.exists():

        return _result(
            False,
            folder=str(path),
            error=f"Folder does not exist: {path}",
        )

    if not path.is_dir():

        return _result(
            False,
            folder=str(path),
            error=f"Not a folder: {path}",
        )

    try:

        result = _run(
            [
                "open",
                str(path),
            ]
        )

        return _result(
            result.returncode == 0,
            folder=str(path),
            message=(
                f"Opened {path}."
                if result.returncode == 0
                else "Unable to open folder."
            ),
            error=(
                result.stderr.strip()
                if result.returncode != 0
                else None
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


def open_home_folder() -> dict:
    return open_folder("home")


def open_desktop() -> dict:
    return open_folder("desktop")


def open_documents() -> dict:
    return open_folder("documents")


def open_downloads() -> dict:
    return open_folder("downloads")


# ============================================================
# CLIPBOARD
# ============================================================

def get_clipboard() -> dict:

    try:

        result = _run(["pbpaste"])

        return _result(
            result.returncode == 0,
            clipboard=result.stdout,
            error=(
                result.stderr.strip()
                if result.returncode != 0
                else None
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


def set_clipboard(
    text: str,
) -> dict:

    if text is None:

        return _result(
            False,
            error="No clipboard text provided.",
        )

    try:

        process = subprocess.Popen(
            ["pbcopy"],
            stdin=subprocess.PIPE,
        )

        process.communicate(
            str(text).encode("utf-8")
        )

        return _result(
            process.returncode == 0,
            message=(
                "Clipboard updated."
                if process.returncode == 0
                else "Unable to update clipboard."
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# VOLUME
# ============================================================

def set_volume(
    level: int | float,
) -> dict:

    try:

        value = max(
            0,
            min(
                100,
                float(level),
            ),
        )

        value = int(value)

        result = _run(
            [
                "osascript",
                "-e",
                f"set volume output volume {value}",
            ]
        )

        return _result(
            result.returncode == 0,
            volume=value,
            message=(
                f"Volume set to {value}%."
                if result.returncode == 0
                else "Unable to set volume."
            ),
            error=(
                result.stderr.strip()
                if result.returncode != 0
                else None
            ),
        )

    except (ValueError, TypeError):

        return _result(
            False,
            error="Volume must be a number between 0 and 100.",
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


def get_volume() -> dict:

    script = (
        'output volume of (get volume settings)'
    )

    try:

        result = _run(
            [
                "osascript",
                "-e",
                script,
            ]
        )

        if result.returncode != 0:

            return _result(
                False,
                error=result.stderr.strip(),
            )

        volume = int(
            result.stdout.strip()
        )

        return _result(
            True,
            volume=volume,
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


def mute_audio() -> dict:

    try:

        result = _run(
            [
                "osascript",
                "-e",
                "set volume with output muted",
            ]
        )

        return _result(
            result.returncode == 0,
            message=(
                "Audio muted."
                if result.returncode == 0
                else "Unable to mute audio."
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


def unmute_audio() -> dict:

    try:

        result = _run(
            [
                "osascript",
                "-e",
                "set volume without output muted",
            ]
        )

        return _result(
            result.returncode == 0,
            message=(
                "Audio unmuted."
                if result.returncode == 0
                else "Unable to unmute audio."
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# BATTERY
# ============================================================

def get_battery_status() -> dict:

    try:

        result = _run(
            [
                "pmset",
                "-g",
                "batt",
            ]
        )

        output = result.stdout.strip()

        percentage = None

        match = re.search(
            r"(\d+)%",
            output,
        )

        if match:
            percentage = int(match.group(1))

        charging = (
            "AC Power" in output
            or "charging" in output.lower()
        )

        return _result(
            result.returncode == 0,
            percentage=percentage,
            charging=charging,
            raw=output,
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# DATE / TIME
# ============================================================

def get_datetime() -> dict:

    now = dt.datetime.now()

    return _result(
        True,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S"),
        day=now.strftime("%A"),
        formatted=now.strftime(
            "%A, %d %B %Y at %I:%M %p"
        ),
        timestamp=now.isoformat(),
    )


# ============================================================
# SAFE CALCULATOR
# ============================================================

_ALLOWED_OPERATORS = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
)


def _safe_calculate_node(node: ast.AST) -> float:

    if isinstance(node, ast.Expression):
        return _safe_calculate_node(node.body)

    if isinstance(node, ast.Constant):

        if isinstance(
            node.value,
            (int, float),
        ):
            return node.value

        raise ValueError(
            "Invalid calculator value."
        )

    if isinstance(node, ast.UnaryOp):

        if not isinstance(
            node.op,
            _ALLOWED_OPERATORS,
        ):
            raise ValueError(
                "Operator not allowed."
            )

        value = _safe_calculate_node(
            node.operand
        )

        if isinstance(node.op, ast.USub):
            return -value

        return value

    if isinstance(node, ast.BinOp):

        if not isinstance(
            node.op,
            _ALLOWED_OPERATORS,
        ):
            raise ValueError(
                "Operator not allowed."
            )

        left = _safe_calculate_node(
            node.left
        )

        right = _safe_calculate_node(
            node.right
        )

        if isinstance(node.op, ast.Add):
            return left + right

        if isinstance(node.op, ast.Sub):
            return left - right

        if isinstance(node.op, ast.Mult):
            return left * right

        if isinstance(node.op, ast.Div):

            if right == 0:
                raise ValueError(
                    "Division by zero."
                )

            return left / right

        if isinstance(node.op, ast.Mod):

            if right == 0:
                raise ValueError(
                    "Modulo by zero."
                )

            return left % right

        if isinstance(node.op, ast.Pow):

            if abs(right) > 100:
                raise ValueError(
                    "Exponent too large."
                )

            return left ** right

    raise ValueError(
        "Invalid mathematical expression."
    )


def calculate(
    expression: str,
) -> dict:

    if not expression:

        return _result(
            False,
            error="No expression provided.",
        )

    expression = (
        str(expression)
        .replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
    )

    try:

        tree = ast.parse(
            expression,
            mode="eval",
        )

        result = _safe_calculate_node(tree)

        return _result(
            True,
            expression=expression,
            result=result,
        )

    except Exception as error:

        return _result(
            False,
            expression=expression,
            error=str(error),
        )


# ============================================================
# TEXT FILES
# ============================================================

def create_text_file(
    filename: str,
    content: str,
    directory: str | None = None,
) -> dict:

    if not filename:

        return _result(
            False,
            error="No filename provided.",
        )

    base_directory = (
        Path(directory).expanduser()
        if directory
        else HOME / "Desktop"
    )

    try:

        base_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = (
            base_directory /
            Path(filename).name
        )

        path.write_text(
            str(content),
            encoding="utf-8",
        )

        return _result(
            True,
            path=str(path),
            message=f"Created {path}.",
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


def read_text_file(
    filepath: str,
) -> dict:

    if not filepath:

        return _result(
            False,
            error="No file specified.",
        )

    path = Path(filepath).expanduser()

    if not path.exists():

        return _result(
            False,
            error=f"File does not exist: {path}",
        )

    if not path.is_file():

        return _result(
            False,
            error=f"Not a file: {path}",
        )

    try:

        content = path.read_text(
            encoding="utf-8"
        )

        return _result(
            True,
            path=str(path),
            content=content,
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


def write_text_file(
    filepath: str,
    content: str,
) -> dict:

    if not filepath:

        return _result(
            False,
            error="No file specified.",
        )

    path = Path(filepath).expanduser()

    try:

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            str(content),
            encoding="utf-8",
        )

        return _result(
            True,
            path=str(path),
            message=f"Saved {path}.",
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# LOCK MAC
# ============================================================

def lock_mac() -> dict:

    try:

        result = _run(
            [
                "pmset",
                "displaysleepnow",
            ]
        )

        return _result(
            result.returncode == 0,
            message=(
                "Mac locked."
                if result.returncode == 0
                else "Unable to lock Mac."
            ),
            error=(
                result.stderr.strip()
                if result.returncode != 0
                else None
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# SCREENSHOT
# ============================================================

def take_screenshot(
    filename: str | None = None,
) -> dict:

    try:

        if filename:

            path = Path(
                filename
            ).expanduser()

        else:

            timestamp = dt.datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            path = (
                HOME
                / "Desktop"
                / f"NOVA_Screenshot_{timestamp}.png"
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        result = _run(
            [
                "screencapture",
                "-x",
                str(path),
            ]
        )

        return _result(
            result.returncode == 0,
            path=str(path),
            message=(
                f"Screenshot saved to {path}."
                if result.returncode == 0
                else "Unable to take screenshot."
            ),
            error=(
                result.stderr.strip()
                if result.returncode != 0
                else None
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# ACTIVE APPLICATION
# ============================================================

def get_active_application() -> dict:

    script = (
        'tell application "System Events" '
        'to get name of first application '
        'process whose frontmost is true'
    )

    try:

        result = _run(
            [
                "osascript",
                "-e",
                script,
            ]
        )

        return _result(
            result.returncode == 0,
            application=(
                result.stdout.strip()
                if result.returncode == 0
                else None
            ),
            error=(
                result.stderr.strip()
                if result.returncode != 0
                else None
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# SHELL COMMAND
# ============================================================

def run_shell_command(
    command: str,
    timeout: int = 30,
) -> dict:

    if not command:

        return _result(
            False,
            error="No shell command provided.",
        )

    try:

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return _result(
            result.returncode == 0,
            command=command,
            return_code=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
        )

    except subprocess.TimeoutExpired:

        return _result(
            False,
            command=command,
            error=(
                f"Command timed out after "
                f"{timeout} seconds."
            ),
        )

    except Exception as error:

        return _result(
            False,
            command=command,
            error=str(error),
        )


# ============================================================
# TOOL STATUS
# ============================================================

def get_tool_status() -> dict:

    tools = [
        name
        for name, value in globals().items()
        if callable(value)
        and not name.startswith("_")
        and name not in {
            "Any",
            "Path",
        }
    ]

    return {
        "success": True,
        "platform": platform.system(),
        "platform_version": platform.platform(),
        "python_version": platform.python_version(),
        "tool_count": len(tools),
        "tools": sorted(tools),
        "application_aliases": len(
            APPLICATION_ALIASES
        ),
        "website_shortcuts": len(
            WEBSITE_SHORTCUTS
        ),
    }


# ============================================================
# SELF TEST
# ============================================================

def self_test() -> dict:

    tests: dict[str, Any] = {}

    test_functions = {
        "system_info": get_system_info,
        "datetime": get_datetime,
        "battery": get_battery_status,
        "active_application": get_active_application,
        "tool_status": get_tool_status,
        "calculator": lambda: calculate("12 * 8 + 5"),
    }

    for name, function in test_functions.items():

        try:

            tests[name] = function()

        except Exception as error:

            tests[name] = {
                "success": False,
                "error": str(error),
            }

    success = all(
        value.get("success", False)
        for value in tests.values()
        if isinstance(value, dict)
    )

    return {
        "success": success,
        "tests": tests,
    }


# ============================================================
# MODULE ENTRY
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("NOVA ADVANCED SYSTEM TOOLS")
    print("=" * 60)

    print()
    print("SYSTEM")
    print("-" * 60)
    print(get_system_info())

    print()
    print("TOOL STATUS")
    print("-" * 60)
    print(get_tool_status())

    print()
    print("SELF TEST")
    print("-" * 60)
    print(self_test())

    print()
    print("=" * 60)
    print("NOVA SYSTEM TOOLS READY")
    print("=" * 60)