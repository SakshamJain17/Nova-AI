from __future__ import annotations

"""
============================================================
NOVA ADVANCED SYSTEM TOOLS
============================================================

macOS system-control layer for NOVA.

Capabilities:
    • Application launching
    • Application closing
    • Application detection
    • Website opening
    • New browser tab
    • Folder opening
    • Home folder
    • Clipboard read/write
    • Volume control
    • Mute/unmute
    • Battery information
    • Date/time
    • Calculator
    • Text-file creation
    • Mac locking
    • Screenshot
    • Active application
    • Shell commands
    • Application aliases
    • Robust macOS application discovery

Designed for:
    macOS
    Apple Silicon
    Python 3.12+

============================================================
"""

import ast
import datetime
import os
import platform
import re
import shutil
import subprocess
import tempfile
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


# ============================================================
# APPLICATION ALIASES
# ============================================================

APPLICATION_ALIASES = {

    # --------------------------------------------------------
    # Apple
    # --------------------------------------------------------

    "safari":
        "Safari",

    "browser":
        "Safari",

    "finder":
        "Finder",

    "file manager":
        "Finder",

    "terminal":
        "Terminal",

    "system settings":
        "System Settings",

    "settings":
        "System Settings",

    "messages":
        "Messages",

    "imessage":
        "Messages",

    "facetime":
        "FaceTime",

    "mail":
        "Mail",

    "apple mail":
        "Mail",

    "calendar":
        "Calendar",

    "notes":
        "Notes",

    "reminders":
        "Reminders",

    "photos":
        "Photos",

    "music":
        "Music",

    "apple music":
        "Music",

    "maps":
        "Maps",

    "calculator":
        "Calculator",

    "preview":
        "Preview",

    "activity monitor":
        "Activity Monitor",

    "disk utility":
        "Disk Utility",

    "textedit":
        "TextEdit",

    "text edit":
        "TextEdit",

    "app store":
        "App Store",

    "system information":
        "System Information",


    # --------------------------------------------------------
    # Browsers
    # --------------------------------------------------------

    "chrome":
        "Google Chrome",

    "google chrome":
        "Google Chrome",

    "firefox":
        "Firefox",

    "mozilla":
        "Firefox",

    "arc":
        "Arc",

    "brave":
        "Brave Browser",

    "brave browser":
        "Brave Browser",

    "edge":
        "Microsoft Edge",

    "microsoft edge":
        "Microsoft Edge",


    # --------------------------------------------------------
    # Development
    # --------------------------------------------------------

    "vscode":
        "Visual Studio Code",

    "vs code":
        "Visual Studio Code",

    "vs-code":
        "Visual Studio Code",

    "visual studio code":
        "Visual Studio Code",

    "code":
        "Visual Studio Code",

    "visual studio":
        "Visual Studio",

    "xcode":
        "Xcode",

    "pycharm":
        "PyCharm",

    "intellij":
        "IntelliJ IDEA",

    "intellij idea":
        "IntelliJ IDEA",

    "webstorm":
        "WebStorm",

    "sublime":
        "Sublime Text",

    "sublime text":
        "Sublime Text",

    "cursor":
        "Cursor",

    "android studio":
        "Android Studio",

    "postman":
        "Postman",

    "docker":
        "Docker",

    "github desktop":
        "GitHub Desktop",


    # --------------------------------------------------------
    # Communication
    # --------------------------------------------------------

    "whatsapp":
        "WhatsApp",

    "whatsapp desktop":
        "WhatsApp",

    "wa":
        "WhatsApp",

    "telegram":
        "Telegram",

    "telegram desktop":
        "Telegram",

    "discord":
        "Discord",

    "slack":
        "Slack",

    "zoom":
        "zoom.us",

    "zoom meeting":
        "zoom.us",

    "teams":
        "Microsoft Teams",

    "microsoft teams":
        "Microsoft Teams",

    "skype":
        "Skype",


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

    "outlook":
        "Microsoft Outlook",

    "onenote":
        "Microsoft OneNote",


    # --------------------------------------------------------
    # Media
    # --------------------------------------------------------

    "spotify":
        "Spotify",

    "vlc":
        "VLC",

    "vlc player":
        "VLC",

    "obs":
        "OBS",

    "obs studio":
        "OBS",

    "steam":
        "Steam",


    # --------------------------------------------------------
    # Creative
    # --------------------------------------------------------

    "photoshop":
        "Adobe Photoshop",

    "adobe photoshop":
        "Adobe Photoshop",

    "premiere":
        "Adobe Premiere Pro",

    "premiere pro":
        "Adobe Premiere Pro",

    "adobe premiere":
        "Adobe Premiere Pro",

    "illustrator":
        "Adobe Illustrator",

    "adobe illustrator":
        "Adobe Illustrator",

    "lightroom":
        "Adobe Lightroom",


    # --------------------------------------------------------
    # Productivity
    # --------------------------------------------------------

    "notion":
        "Notion",

    "evernote":
        "Evernote",

    "todoist":
        "Todoist",

    "dropbox":
        "Dropbox",

    "google drive":
        "Google Drive",

}


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _result(
    success: bool,
    **kwargs: Any,
) -> dict:

    return {
        "success": success,
        **kwargs,
    }


def _run(
    command: list[str],
    timeout: float = 15,
) -> subprocess.CompletedProcess:

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _normalize_name(
    application: str,
) -> str:

    if not application:

        return application

    cleaned = (
        str(application)
        .strip()
        .lower()
        .strip("\"'")
    )

    return APPLICATION_ALIASES.get(
        cleaned,
        str(application).strip(),
    )


def _application_directories() -> list[Path]:

    return [
        directory
        for directory in APPLICATION_DIRECTORIES
        if directory.exists()
    ]


def _find_application(
    application: str,
) -> str | None:

    if not application:

        return None

    target = application.lower().strip()

    # --------------------------------------------------------
    # Remove .app if user supplied it
    # --------------------------------------------------------

    if target.endswith(".app"):

        target = target[:-4]


    # --------------------------------------------------------
    # Exact path
    # --------------------------------------------------------

    possible_path = Path(application).expanduser()

    if possible_path.exists():

        return str(possible_path)


    # --------------------------------------------------------
    # Exact application name
    # --------------------------------------------------------

    for directory in _application_directories():

        candidate = (
            directory /
            f"{application}.app"
        )

        if candidate.exists():

            return str(candidate)


    # --------------------------------------------------------
    # Case-insensitive application search
    # --------------------------------------------------------

    for directory in _application_directories():

        try:

            for item in directory.iterdir():

                if not item.name.lower().endswith(
                    ".app"
                ):
                    continue

                app_name = item.stem.lower()

                if app_name == target:

                    return str(item)

        except (
            PermissionError,
            OSError,
        ):

            continue


    # --------------------------------------------------------
    # Partial match
    # --------------------------------------------------------

    for directory in _application_directories():

        try:

            for item in directory.iterdir():

                if not item.name.lower().endswith(
                    ".app"
                ):
                    continue

                app_name = item.stem.lower()

                if (
                    target in app_name
                    or app_name in target
                ):

                    return str(item)

        except (
            PermissionError,
            OSError,
        ):

            continue


    return None


# ============================================================
# SYSTEM INFORMATION
# ============================================================

def get_system_info() -> dict:

    try:

        macos_version = platform.mac_ver()[0]

        processor = (
            platform.machine()
        )

        hostname = (
            platform.node()
        )

        username = (
            os.environ.get(
                "USER",
                os.environ.get(
                    "USERNAME",
                    "unknown",
                ),
            )
        )

        python_version = (
            platform.python_version()
        )

        return _result(
            True,
            operating_system=SYSTEM,
            macos_version=macos_version,
            processor=processor,
            hostname=hostname,
            user=username,
            python_version=python_version,
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# APPLICATION STATUS
# ============================================================

def get_installed_applications() -> dict:

    applications = []

    for directory in _application_directories():

        try:

            for item in directory.iterdir():

                if item.name.endswith(".app"):

                    applications.append(
                        item.stem
                    )

        except (
            PermissionError,
            OSError,
        ):

            continue

    applications = sorted(
        set(applications),
        key=str.lower,
    )

    return _result(
        True,
        count=len(applications),
        applications=applications,
    )


def is_application_installed(
    application: str,
) -> dict:

    resolved = _normalize_name(
        application
    )

    path = _find_application(
        resolved
    )

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

def open_application(application: str):
    """
    Open and activate a macOS application.

    Uses `open -a` followed by AppleScript activation so that
    the application's actual window is brought to the foreground.
    """

    import subprocess

    if not application:
        return {
            "success": False,
            "error": "No application specified."
        }

    aliases = {
        "calculator": "Calculator",
        "calc": "Calculator",

        "whatsapp": "WhatsApp",

        "vs code": "Visual Studio Code",
        "vscode": "Visual Studio Code",
        "visual studio code": "Visual Studio Code",

        "safari": "Safari",

        "chrome": "Google Chrome",
        "google chrome": "Google Chrome",

        "finder": "Finder",

        "terminal": "Terminal",

        "spotify": "Spotify",

        "discord": "Discord",

        "messages": "Messages",

        "mail": "Mail",

        "notes": "Notes",

        "calendar": "Calendar",

        "photos": "Photos",

        "settings": "System Settings",
        "system settings": "System Settings",
    }

    requested = str(application).strip()

    normalized = requested.lower()

    app_name = aliases.get(
        normalized,
        requested
    )

    try:
        # ----------------------------------------------------
        # Launch the application
        # ----------------------------------------------------

        launch = subprocess.run(
            [
                "open",
                "-a",
                app_name
            ],
            capture_output=True,
            text=True,
            timeout=15
        )

        if launch.returncode != 0:

            error = (
                launch.stderr.strip()
                or f"Could not open {app_name}."
            )

            return {
                "success": False,
                "application": app_name,
                "error": error
            }

        # ----------------------------------------------------
        # Explicitly activate the application.
        #
        # This is important on macOS because an application can
        # be running without its window being in the foreground.
        # ----------------------------------------------------

        apple_script = f'''
        tell application "{app_name}"
            activate
        end tell
        '''

        activate = subprocess.run(
            [
                "osascript",
                "-e",
                apple_script
            ],
            capture_output=True,
            text=True,
            timeout=15
        )

        if activate.returncode != 0:

            return {
                "success": True,
                "application": app_name,
                "message": (
                    f"{app_name} launched, "
                    "but macOS could not activate its window."
                )
            }

        return {
            "success": True,
            "application": app_name,
            "message": f"Opened and activated {app_name}."
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "application": app_name,
            "error": "Application launch timed out."
        }

    except Exception as error:

        return {
            "success": False,
            "application": app_name,
            "error": str(error)
        }


    # --------------------------------------------------------
    # First attempt: macOS LaunchServices
    # --------------------------------------------------------

    try:

        result = _run(
            [
                "open",
                "-a",
                resolved,
            ]
        )

        if result.returncode == 0:

            return _result(
                True,
                application=resolved,
                message=(
                    f"Opened {resolved}."
                ),
            )

    except Exception:
        pass


    # --------------------------------------------------------
    # Find application manually
    # --------------------------------------------------------

    path = _find_application(
        resolved
    )

    if path:

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
                    message=(
                        f"Opened {resolved}."
                    ),
                )

            return _result(
                False,
                application=resolved,
                path=path,
                error=(
                    result.stderr.strip()
                    or
                    "macOS could not open the application."
                ),
            )

        except Exception as error:

            return _result(
                False,
                application=resolved,
                path=path,
                error=str(error),
            )


    return _result(
        False,
        application=resolved,
        error=(
            f"Unable to find '{resolved}' "
            "on this Mac. "
            "Make sure it is installed."
        ),
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

    resolved = _normalize_name(
        application
    )

    script = (
        'tell application '
        f'"{resolved}" '
        'to quit'
    )

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
                application=resolved,
                message=(
                    f"Closed {resolved}."
                ),
            )

        return _result(
            False,
            application=resolved,
            error=(
                result.stderr.strip()
                or
                f"Could not close {resolved}."
            ),
        )

    except Exception as error:

        return _result(
            False,
            application=resolved,
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

    url = url.strip()

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

        if result.returncode == 0:

            return _result(
                True,
                url=url,
                message=(
                    f"Opened {url}."
                ),
            )

        return _result(
            False,
            url=url,
            error=(
                result.stderr.strip()
                or
                "Unable to open website."
            ),
        )

    except Exception as error:

        return _result(
            False,
            url=url,
            error=str(error),
        )


# ============================================================
# OPEN WEBSITE IN NEW TAB
# ============================================================

def open_website_new_tab(
    url: str,
) -> dict:

    if not url:

        return _result(
            False,
            error="No URL provided.",
        )

    url = url.strip()

    if not re.match(
        r"^https?://",
        url,
        re.IGNORECASE,
    ):

        url = "https://" + url

    try:

        script = (
            'tell application "Safari"\n'
            'activate\n'
            'tell window 1\n'
            'make new tab with properties '
            f'{{URL:"{url}"}}\n'
            'end tell\n'
            'end tell'
        )

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

        # ----------------------------------------------------
        # Fallback to default browser
        # ----------------------------------------------------

        return open_website(
            url
        )

    except Exception as error:

        return _result(
            False,
            url=url,
            error=str(error),
        )


# ============================================================
# OPEN FOLDER
# ============================================================

def open_folder(
    folder: str,
) -> dict:

    if not folder:

        return _result(
            False,
            error="No folder specified.",
        )

    path = Path(
        folder
    ).expanduser()

    if not path.exists():

        return _result(
            False,
            folder=str(path),
            error=(
                f"Folder does not exist: {path}"
            ),
        )

    try:

        result = _run(
            [
                "open",
                str(path),
            ]
        )

        if result.returncode == 0:

            return _result(
                True,
                folder=str(path),
                message=(
                    f"Opened {path}."
                ),
            )

        return _result(
            False,
            folder=str(path),
            error=(
                result.stderr.strip()
                or
                "Unable to open folder."
            ),
        )

    except Exception as error:

        return _result(
            False,
            folder=str(path),
            error=str(error),
        )


# ============================================================
# HOME FOLDER
# ============================================================

def open_home_folder() -> dict:

    return open_folder(
        str(HOME)
    )


# ============================================================
# CLIPBOARD
# ============================================================

def get_clipboard() -> dict:

    try:

        result = _run(
            [
                "pbpaste"
            ]
        )

        if result.returncode == 0:

            return _result(
                True,
                clipboard=result.stdout,
            )

        return _result(
            False,
            error=(
                result.stderr.strip()
                or
                "Unable to read clipboard."
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
            [
                "pbcopy"
            ],
            stdin=subprocess.PIPE,
        )

        process.communicate(
            str(text).encode(
                "utf-8"
            )
        )

        if process.returncode == 0:

            return _result(
                True,
                message="Clipboard updated.",
            )

        return _result(
            False,
            error="Unable to update clipboard.",
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

        level = float(level)

        level = max(
            0,
            min(
                100,
                level,
            ),
        )

        result = _run(
            [
                "osascript",
                "-e",
                (
                    f"set volume output volume "
                    f"{int(level)}"
                ),
            ]
        )

        if result.returncode == 0:

            return _result(
                True,
                volume=int(level),
                message=(
                    f"Volume set to {int(level)}%."
                ),
            )

        return _result(
            False,
            error=(
                result.stderr.strip()
                or
                "Unable to set volume."
            ),
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
            message="Audio muted."
            if result.returncode == 0
            else "Unable to mute audio.",
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
            message="Audio unmuted."
            if result.returncode == 0
            else "Unable to unmute audio.",
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
            r"(\d+)%"
            ,
            output
        )

        if match:

            percentage = int(
                match.group(1)
            )

        charging = (
            "AC Power"
            in output
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

    now = datetime.datetime.now()

    return _result(
        True,
        date=now.strftime(
            "%Y-%m-%d"
        ),
        time=now.strftime(
            "%H:%M:%S"
        ),
        day=now.strftime(
            "%A"
        ),
        formatted=now.strftime(
            "%A, %d %B %Y at %I:%M %p"
        ),
        timestamp=now.isoformat(),
    )


# ============================================================
# CALCULATOR
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


def _safe_calculate_node(
    node,
):

    if isinstance(
        node,
        ast.Expression,
    ):

        return _safe_calculate_node(
            node.body
        )

    if isinstance(
        node,
        ast.Constant,
    ):

        if isinstance(
            node.value,
            (int, float),
        ):

            return node.value

        raise ValueError(
            "Invalid calculator value."
        )

    if isinstance(
        node,
        ast.UnaryOp,
    ):

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

        if isinstance(
            node.op,
            ast.USub,
        ):

            return -value

        return value

    if isinstance(
        node,
        ast.BinOp,
    ):

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

        if isinstance(
            node.op,
            ast.Add,
        ):

            return left + right

        if isinstance(
            node.op,
            ast.Sub,
        ):

            return left - right

        if isinstance(
            node.op,
            ast.Mult,
        ):

            return left * right

        if isinstance(
            node.op,
            ast.Div,
        ):

            return left / right

        if isinstance(
            node.op,
            ast.Pow,
        ):

            if abs(right) > 100:

                raise ValueError(
                    "Exponent too large."
                )

            return left ** right

        if isinstance(
            node.op,
            ast.Mod,
        ):

            return left % right

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

    try:

        expression = (
            expression
            .replace("×", "*")
            .replace("÷", "/")
            .replace("−", "-")
        )

        tree = ast.parse(
            expression,
            mode="eval",
        )

        result = _safe_calculate_node(
            tree
        )

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
# CREATE TEXT FILE
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

    if directory:

        base_directory = Path(
            directory
        ).expanduser()

    else:

        base_directory = (
            HOME / "Desktop"
        )

    try:

        base_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = (
            base_directory /
            filename
        )

        path.write_text(
            str(content),
            encoding="utf-8",
        )

        return _result(
            True,
            path=str(path),
            message=(
                f"Created {path}."
            ),
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

            timestamp = datetime.datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            path = (
                HOME /
                "Desktop" /
                f"NOVA_Screenshot_{timestamp}.png"
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

        if result.returncode == 0:

            return _result(
                True,
                path=str(path),
                message=(
                    f"Screenshot saved to {path}."
                ),
            )

        return _result(
            False,
            error=(
                result.stderr.strip()
                or
                "Unable to take screenshot."
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

    try:

        script = (
            'tell application "System Events" '
            'to get name of first application '
            'process whose frontmost is true'
        )

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
                application=result.stdout.strip(),
            )

        return _result(
            False,
            error=(
                result.stderr.strip()
                or
                "Unable to detect active application."
            ),
        )

    except Exception as error:

        return _result(
            False,
            error=str(error),
        )


# ============================================================
# RUN SHELL COMMAND
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
# WEBSITE SHORTCUTS
# ============================================================

WEBSITE_SHORTCUTS = {

    "youtube":
        "https://youtube.com",

    "youtube.com":
        "https://youtube.com",

    "google":
        "https://google.com",

    "gmail":
        "https://mail.google.com",

    "whatsapp web":
        "https://web.whatsapp.com",

    "github":
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

    "x":
        "https://x.com",

    "twitter":
        "https://x.com",

    "amazon":
        "https://amazon.in",

    "netflix":
        "https://netflix.com",

    "spotify web":
        "https://open.spotify.com",

}


def open_shortcut(
    name: str,
) -> dict:

    if not name:

        return _result(
            False,
            error="No shortcut provided.",
        )

    key = (
        name
        .strip()
        .lower()
    )

    url = WEBSITE_SHORTCUTS.get(
        key
    )

    if not url:

        return _result(
            False,
            error=(
                f"No website shortcut exists "
                f"for '{name}'."
            ),
        )

    return open_website(
        url
    )


# ============================================================
# TOOL STATUS
# ============================================================

def get_tool_status() -> dict:

    tools = [

        "get_system_info",

        "get_installed_applications",

        "is_application_installed",

        "open_application",

        "close_application",

        "open_website",

        "open_website_new_tab",

        "open_shortcut",

        "open_folder",

        "open_home_folder",

        "get_clipboard",

        "set_clipboard",

        "set_volume",

        "mute_audio",

        "unmute_audio",

        "get_battery_status",

        "get_datetime",

        "calculate",

        "create_text_file",

        "lock_mac",

        "take_screenshot",

        "get_active_application",

        "run_shell_command",

    ]

    return {
        "platform": platform.system(),
        "platform_version": platform.platform(),
        "tools": tools,
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

    results = {}


    # System info

    try:

        results["system_info"] = (
            get_system_info()
        )

    except Exception as error:

        results["system_info"] = {
            "success": False,
            "error": str(error),
        }


    # Date/time

    try:

        results["datetime"] = (
            get_datetime()
        )

    except Exception as error:

        results["datetime"] = {
            "success": False,
            "error": str(error),
        }


    # Battery

    try:

        results["battery"] = (
            get_battery_status()
        )

    except Exception as error:

        results["battery"] = {
            "success": False,
            "error": str(error),
        }


    # Active application

    try:

        results["active_application"] = (
            get_active_application()
        )

    except Exception as error:

        results["active_application"] = {
            "success": False,
            "error": str(error),
        }


    return {
        "success": True,
        "tests": results,
    }


# ============================================================
# MODULE READY
# ============================================================

if __name__ == "__main__":

    print(
        "NOVA SYSTEM TOOLS"
    )

    print(
        "=" * 50
    )

    print(
        get_tool_status()
    )

    print()

    print(
        "System:"
    )

    print(
        get_system_info()
    )

    print()

    print(
        "Installed application count:"
    )

    print(
        get_installed_applications()
    )
