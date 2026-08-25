from __future__ import annotations

"""
NOVA Profile Engine
===================

Persistent identity and user-profile layer for NOVA.

Responsibilities:
    - Store canonical user identity
    - Store stable preferences
    - Store goals
    - Store interests
    - Store projects
    - Store communication preferences
    - Provide safe profile context to the LLM
    - Prevent speech-recognition name corruption
    - Avoid storing arbitrary conversation as profile data

This module intentionally does NOT replace memory.py.
memory.py = general memories
profile.py = stable user identity and profile
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
import json
import logging


# ============================================================
# CONFIGURATION
# ============================================================

PROFILE_VERSION = 1

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

PROFILE_FILE = DATA_DIR / "nova_profile.json"

DEFAULT_USER_NAME = "Saksham"

DEFAULT_ASSISTANT_NAME = "NOVA"


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger("NOVA.Profile")

if not logger.handlers:

    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "[NOVA PROFILE %(levelname)s] %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)

logger.setLevel(logging.INFO)


# ============================================================
# LOCK
# ============================================================

_lock = RLock()


# ============================================================
# PROFILE MODEL
# ============================================================

@dataclass
class UserProfile:

    version: int = PROFILE_VERSION

    # --------------------------------------------------------
    # Identity
    # --------------------------------------------------------

    name: str = DEFAULT_USER_NAME

    assistant_name: str = DEFAULT_ASSISTANT_NAME

    preferred_title: str = "Boss"

    # --------------------------------------------------------
    # Communication
    # --------------------------------------------------------

    preferred_language: str = "English"

    response_style: str = "natural"

    verbosity: str = "adaptive"

    allow_proactive_suggestions: bool = True

    # --------------------------------------------------------
    # Personal information
    # --------------------------------------------------------

    interests: list[str] = field(
        default_factory=list
    )

    goals: list[str] = field(
        default_factory=list
    )

    projects: list[str] = field(
        default_factory=list
    )

    skills: list[str] = field(
        default_factory=list
    )

    preferences: dict[str, str] = field(
        default_factory=dict
    )

    # --------------------------------------------------------
    # NOVA behaviour
    # --------------------------------------------------------

    favorite_apps: list[str] = field(
        default_factory=list
    )

    frequent_tasks: list[str] = field(
        default_factory=list
    )

    enabled_features: list[str] = field(
        default_factory=list
    )

    disabled_features: list[str] = field(
        default_factory=list
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    created_at: str = ""

    updated_at: str = ""


# ============================================================
# PROFILE MANAGER
# ============================================================

class ProfileManager:

    def __init__(
        self,
        path: Path = PROFILE_FILE,
    ):

        self.path = Path(path)

        self.profile = UserProfile()

        self._ensure_directory()

        self.load()


    # ========================================================
    # DIRECTORY
    # ========================================================

    def _ensure_directory(self) -> None:

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


    # ========================================================
    # TIME
    # ========================================================

    @staticmethod
    def _now() -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()


    # ========================================================
    # LOAD
    # ========================================================

    def load(self) -> UserProfile:

        with _lock:

            if not self.path.exists():

                now = self._now()

                self.profile.created_at = now
                self.profile.updated_at = now

                self.save()

                return self.profile

            try:

                with self.path.open(
                    "r",
                    encoding="utf-8",
                ) as file:

                    data = json.load(file)

                if not isinstance(
                    data,
                    dict,
                ):

                    raise ValueError(
                        "Profile JSON must contain an object."
                    )

                self.profile = (
                    self._from_dict(data)
                )

            except Exception as error:

                logger.warning(
                    "Profile could not be loaded: %s",
                    error,
                )

                # Never destroy a valid profile
                # because of malformed data.

                backup = (
                    self.path.with_suffix(
                        ".corrupt.json"
                    )
                )

                try:

                    self.path.replace(
                        backup
                    )

                    logger.warning(
                        "Corrupt profile moved to %s",
                        backup,
                    )

                except Exception:

                    pass

                self.profile = UserProfile()

                now = self._now()

                self.profile.created_at = now
                self.profile.updated_at = now

                self.save()

            return self.profile


    # ========================================================
    # SAFE DESERIALIZATION
    # ========================================================

    @staticmethod
    def _from_dict(
        data: dict[str, Any],
    ) -> UserProfile:

        defaults = UserProfile()

        allowed = {
            field_name
            for field_name in defaults.__dataclass_fields__
        }

        cleaned: dict[str, Any] = {}

        for key in allowed:

            if key in data:

                cleaned[key] = data[key]

        profile = UserProfile(
            **cleaned
        )

        # ----------------------------------------------------
        # Enforce canonical identity
        # ----------------------------------------------------

        profile.name = DEFAULT_USER_NAME

        if not profile.assistant_name:

            profile.assistant_name = (
                DEFAULT_ASSISTANT_NAME
            )

        if not profile.preferred_title:

            profile.preferred_title = "Boss"

        # ----------------------------------------------------
        # Type safety
        # ----------------------------------------------------

        profile.interests = (
            _clean_string_list(
                profile.interests
            )
        )

        profile.goals = (
            _clean_string_list(
                profile.goals
            )
        )

        profile.projects = (
            _clean_string_list(
                profile.projects
            )
        )

        profile.skills = (
            _clean_string_list(
                profile.skills
            )
        )

        profile.favorite_apps = (
            _clean_string_list(
                profile.favorite_apps
            )
        )

        profile.frequent_tasks = (
            _clean_string_list(
                profile.frequent_tasks
            )
        )

        profile.enabled_features = (
            _clean_string_list(
                profile.enabled_features
            )
        )

        profile.disabled_features = (
            _clean_string_list(
                profile.disabled_features
            )
        )

        if not isinstance(
            profile.preferences,
            dict,
        ):

            profile.preferences = {}

        return profile


    # ========================================================
    # SAVE
    # ========================================================

    def save(self) -> bool:

        with _lock:

            try:

                self._ensure_directory()

                self.profile.updated_at = (
                    self._now()
                )

                data = asdict(
                    self.profile
                )

                temporary = (
                    self.path.with_suffix(
                        ".tmp"
                    )
                )

                with temporary.open(
                    "w",
                    encoding="utf-8",
                ) as file:

                    json.dump(
                        data,
                        file,
                        indent=4,
                        ensure_ascii=False,
                    )

                # Atomic replacement
                temporary.replace(
                    self.path
                )

                return True

            except Exception as error:

                logger.error(
                    "Profile save failed: %s",
                    error,
                )

                return False


    # ========================================================
    # IDENTITY
    # ========================================================

    def get_name(self) -> str:

        # Absolutely never trust speech recognition
        # for canonical identity.

        return DEFAULT_USER_NAME


    def set_name(
        self,
        name: str,
    ) -> bool:

        """
        Intentionally protects the canonical name.

        The application owner should be changed
        manually in this file/profile system rather
        than through an arbitrary voice transcription.
        """

        if not name:

            return False

        normalized = (
            name.strip()
        )

        if normalized.lower() in {
            "saksham",
            "saxham",
            "saxam",
            "thaksam",
            "thaxam",
        }:

            normalized = DEFAULT_USER_NAME

        # Prevent accidental voice-recognition
        # corruption from changing identity.

        if normalized.lower() != (
            DEFAULT_USER_NAME.lower()
        ):

            logger.warning(
                "Rejected identity change: %s",
                normalized,
            )

            return False

        self.profile.name = (
            DEFAULT_USER_NAME
        )

        return self.save()


    # ========================================================
    # PREFERENCES
    # ========================================================

    def set_preference(
        self,
        key: str,
        value: Any,
    ) -> bool:

        key = str(
            key
        ).strip()

        if not key:

            return False

        self.profile.preferences[
            key
        ] = str(value)

        return self.save()


    def get_preference(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.profile.preferences.get(
            key,
            default,
        )


    def remove_preference(
        self,
        key: str,
    ) -> bool:

        if key not in self.profile.preferences:

            return False

        del self.profile.preferences[
            key
        ]

        return self.save()


    # ========================================================
    # LIST MANAGEMENT
    # ========================================================

    def _add_unique(
        self,
        attribute: str,
        value: str,
    ) -> bool:

        value = str(
            value
        ).strip()

        if not value:

            return False

        values = getattr(
            self.profile,
            attribute,
            None,
        )

        if values is None:

            return False

        # Case-insensitive duplicate check

        if any(
            existing.lower()
            == value.lower()
            for existing in values
        ):

            return False

        values.append(
            value
        )

        return self.save()


    def _remove_value(
        self,
        attribute: str,
        value: str,
    ) -> bool:

        values = getattr(
            self.profile,
            attribute,
            None,
        )

        if not values:

            return False

        value_lower = (
            str(value).strip().lower()
        )

        original_length = len(
            values
        )

        values[:] = [
            item
            for item in values
            if item.lower()
            != value_lower
        ]

        if len(values) == original_length:

            return False

        return self.save()


    # ========================================================
    # INTERESTS
    # ========================================================

    def add_interest(
        self,
        value: str,
    ) -> bool:

        return self._add_unique(
            "interests",
            value,
        )


    def remove_interest(
        self,
        value: str,
    ) -> bool:

        return self._remove_value(
            "interests",
            value,
        )


    # ========================================================
    # GOALS
    # ========================================================

    def add_goal(
        self,
        value: str,
    ) -> bool:

        return self._add_unique(
            "goals",
            value,
        )


    def remove_goal(
        self,
        value: str,
    ) -> bool:

        return self._remove_value(
            "goals",
            value,
        )


    # ========================================================
    # PROJECTS
    # ========================================================

    def add_project(
        self,
        value: str,
    ) -> bool:

        return self._add_unique(
            "projects",
            value,
        )


    def remove_project(
        self,
        value: str,
    ) -> bool:

        return self._remove_value(
            "projects",
            value,
        )


    # ========================================================
    # SKILLS
    # ========================================================

    def add_skill(
        self,
        value: str,
    ) -> bool:

        return self._add_unique(
            "skills",
            value,
        )


    def remove_skill(
        self,
        value: str,
    ) -> bool:

        return self._remove_value(
            "skills",
            value,
        )


    # ========================================================
    # APPLICATIONS
    # ========================================================

    def add_favorite_app(
        self,
        value: str,
    ) -> bool:

        return self._add_unique(
            "favorite_apps",
            value,
        )


    def remove_favorite_app(
        self,
        value: str,
    ) -> bool:

        return self._remove_value(
            "favorite_apps",
            value,
        )


    # ========================================================
    # TASKS
    # ========================================================

    def add_frequent_task(
        self,
        value: str,
    ) -> bool:

        return self._add_unique(
            "frequent_tasks",
            value,
        )


    # ========================================================
    # FEATURES
    # ========================================================

    def enable_feature(
        self,
        feature: str,
    ) -> bool:

        feature = str(
            feature
        ).strip()

        if not feature:

            return False

        self._remove_value(
            "disabled_features",
            feature,
        )

        return self._add_unique(
            "enabled_features",
            feature,
        )


    def disable_feature(
        self,
        feature: str,
    ) -> bool:

        feature = str(
            feature
        ).strip()

        if not feature:

            return False

        self._remove_value(
            "enabled_features",
            feature,
        )

        return self._add_unique(
            "disabled_features",
            feature,
        )


    # ========================================================
    # PROFILE SNAPSHOT
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return asdict(
            self.profile
        )


    # ========================================================
    # LLM CONTEXT
    # ========================================================

    def build_context(
        self,
    ) -> str:

        p = self.profile

        lines = [
            "===== NOVA USER PROFILE =====",
            f"Canonical name: {DEFAULT_USER_NAME}",
            f"Assistant name: {p.assistant_name}",
            f"Preferred title: {p.preferred_title}",
            f"Language: {p.preferred_language}",
            f"Response style: {p.response_style}",
            f"Verbosity: {p.verbosity}",
            (
                "Proactive suggestions: "
                f"{p.allow_proactive_suggestions}"
            ),
        ]

        if p.interests:

            lines.append(
                "Interests: "
                + ", ".join(
                    p.interests
                )
            )

        if p.goals:

            lines.append(
                "Goals: "
                + ", ".join(
                    p.goals
                )
            )

        if p.projects:

            lines.append(
                "Projects: "
                + ", ".join(
                    p.projects
                )
            )

        if p.skills:

            lines.append(
                "Skills: "
                + ", ".join(
                    p.skills
                )
            )

        if p.favorite_apps:

            lines.append(
                "Frequently used apps: "
                + ", ".join(
                    p.favorite_apps
                )
            )

        if p.frequent_tasks:

            lines.append(
                "Frequent tasks: "
                + ", ".join(
                    p.frequent_tasks
                )
            )

        if p.preferences:

            lines.append(
                "Preferences:"
            )

            for key, value in (
                p.preferences.items()
            ):

                lines.append(
                    f"- {key}: {value}"
                )

        lines.append(
            "Identity instruction: "
            "Always address the user as Saksham "
            "when using their name."
        )

        lines.append(
            "===== END USER PROFILE ====="
        )

        return "\n".join(
            lines
        )


    # ========================================================
    # RESET
    # ========================================================

    def reset_profile(
        self,
        preserve_identity: bool = True,
    ) -> bool:

        old_name = self.profile.name

        self.profile = UserProfile()

        if preserve_identity:

            self.profile.name = (
                DEFAULT_USER_NAME
            )

        else:

            self.profile.name = (
                DEFAULT_USER_NAME
            )

        self.profile.created_at = (
            self._now()
        )

        self.profile.updated_at = (
            self._now()
        )

        return self.save()


# ============================================================
# HELPERS
# ============================================================

def _clean_string_list(
    value: Any,
) -> list[str]:

    if not isinstance(
        value,
        list,
    ):

        return []

    result: list[str] = []

    for item in value:

        if not isinstance(
            item,
            str,
        ):

            continue

        item = item.strip()

        if not item:

            continue

        if not any(
            existing.lower()
            == item.lower()
            for existing in result
        ):

            result.append(
                item
            )

    return result


# ============================================================
# GLOBAL PROFILE INSTANCE
# ============================================================

_profile_manager = ProfileManager()


# ============================================================
# PUBLIC API
# ============================================================

def get_profile_manager() -> ProfileManager:

    return _profile_manager


def get_profile() -> dict[str, Any]:

    return _profile_manager.to_dict()


def get_user_name() -> str:

    return DEFAULT_USER_NAME


def get_assistant_name() -> str:

    return _profile_manager.profile.assistant_name


def get_profile_context() -> str:

    return _profile_manager.build_context()


def set_preference(
    key: str,
    value: Any,
) -> bool:

    return _profile_manager.set_preference(
        key,
        value,
    )


def get_preference(
    key: str,
    default: Any = None,
) -> Any:

    return _profile_manager.get_preference(
        key,
        default,
    )


def add_interest(
    value: str,
) -> bool:

    return _profile_manager.add_interest(
        value
    )


def add_goal(
    value: str,
) -> bool:

    return _profile_manager.add_goal(
        value
    )


def add_project(
    value: str,
) -> bool:

    return _profile_manager.add_project(
        value
    )


def add_skill(
    value: str,
) -> bool:

    return _profile_manager.add_skill(
        value
    )


def add_favorite_app(
    value: str,
) -> bool:

    return _profile_manager.add_favorite_app(
        value
    )


def add_frequent_task(
    value: str,
) -> bool:

    return _profile_manager.add_frequent_task(
        value
    )


def enable_feature(
    feature: str,
) -> bool:

    return _profile_manager.enable_feature(
        feature
    )


def disable_feature(
    feature: str,
) -> bool:

    return _profile_manager.disable_feature(
        feature
    )


def profile_health() -> dict[str, Any]:

    profile = _profile_manager.profile

    return {
        "success": True,
        "profile_file": str(
            PROFILE_FILE
        ),
        "exists": PROFILE_FILE.exists(),
        "user_name": DEFAULT_USER_NAME,
        "assistant_name": (
            profile.assistant_name
        ),
        "interests": len(
            profile.interests
        ),
        "goals": len(
            profile.goals
        ),
        "projects": len(
            profile.projects
        ),
        "skills": len(
            profile.skills
        ),
        "preferences": len(
            profile.preferences
        ),
        "favorite_apps": len(
            profile.favorite_apps
        ),
        "frequent_tasks": len(
            profile.frequent_tasks
        ),
        "version": profile.version,
    }


# ============================================================
# INITIAL PROFILE
# ============================================================

def initialize_default_profile() -> bool:

    manager = get_profile_manager()

    changed = False

    if manager.profile.name != DEFAULT_USER_NAME:

        manager.profile.name = (
            DEFAULT_USER_NAME
        )

        changed = True

    if not manager.profile.assistant_name:

        manager.profile.assistant_name = (
            DEFAULT_ASSISTANT_NAME
        )

        changed = True

    if not manager.profile.preferred_title:

        manager.profile.preferred_title = (
            "Boss"
        )

        changed = True

    if changed:

        return manager.save()

    return True


# ============================================================
# STARTUP VALIDATION
# ============================================================

initialize_default_profile()