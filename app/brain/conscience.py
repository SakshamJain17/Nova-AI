from __future__ import annotations

from typing import Any

from app.memory.memory import (
    save_memory,
    get_all_memories,
    search_memories,
    forget_memory,
    save_preference,
    get_preferences,
    delete_preference,
    get_habits,
    record_habit,
)

from app.memory.habits import (
    observe_action,
    get_high_confidence_habits,
    get_frequent_habits,
    get_ranked_habits,
    build_habit_context,
)


# ============================================================
# NOVA CONSCIENCE
# ============================================================
#
# This is NOT literal consciousness.
#
# It is NOVA's persistent personal-context layer.
#
# It allows NOVA to:
#
# - remember explicit information
# - remember preferences
# - observe repeated behavior
# - identify habits
# - build personal context
# - forget information
# - distinguish facts from observations
# - provide relevant context to the LLM
#
# ============================================================


CONSCIENCE_RULES = """
NOVA is an AI assistant with persistent personal context.

NOVA may remember information explicitly provided by the user.

NOVA may recognize repeated behavioral patterns.

NOVA must distinguish:

1. Explicit facts
2. User preferences
3. Observed habits
4. Temporary conversation context
5. AI-generated assumptions

NOVA must never present an assumption as a confirmed fact.

NOVA should use personal information only when relevant.

NOVA must respect requests to forget information.

NOVA must not claim literal human consciousness.

NOVA should address the user as Saksham when appropriate.

The user's name is spelled exactly:

Saksham

Never write it as:
Saksham Jainn
Sakshamjain
or other variations.

If uncertain about a personal fact, say that you are uncertain.
"""


# ============================================================
# REMEMBER
# ============================================================

def remember(
    text: str,
    category: str = "general",
    importance: float = 0.8,
) -> dict[str, Any]:
    """
    Explicitly store a user-provided memory.
    """

    if not text or not text.strip():

        return {
            "success": False,
            "message": "Nothing was provided to remember.",
        }

    success = save_memory(
        memory=text.strip(),
        category=category,
        importance=importance,
        confidence=1.0,
        source="explicit_user",
    )

    return {
        "success": success,
        "memory": text.strip(),
        "category": category,
        "message": (
            "I'll remember that."
            if success
            else "I couldn't save that memory."
        ),
    }


# ============================================================
# FORGET
# ============================================================

def forget(
    text: str,
) -> dict[str, Any]:
    """
    Forget memories matching the supplied text.
    """

    if not text or not text.strip():

        return {
            "success": False,
            "deleted": 0,
            "message": "Nothing was specified to forget.",
        }

    deleted = forget_memory(
        text.strip()
    )

    return {
        "success": True,
        "deleted": deleted,
        "message": (
            f"Forgot {deleted} matching "
            f"memory{'ies' if deleted != 1 else ''}."
        ),
    }


# ============================================================
# SEARCH
# ============================================================

def search_memory(
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Search NOVA's persistent memory.
    """

    if not query or not query.strip():

        return {
            "success": False,
            "results": [],
        }

    results = search_memories(
        query=query,
        limit=limit,
    )

    return {
        "success": True,
        "query": query,
        "results": results,
    }


# ============================================================
# GET WHAT NOVA KNOWS
# ============================================================

def what_i_know() -> dict[str, Any]:
    """
    Return all persistent personal context.
    """

    memories = get_all_memories(
        limit=100
    )

    preferences = get_preferences()

    habits = get_habits(
        limit=100
    )

    return {
        "memories": memories,
        "preferences": preferences,
        "habits": habits,
    }


# ============================================================
# PREFERENCE
# ============================================================

def set_user_preference(
    key: str,
    value: str,
    confidence: float = 1.0,
) -> dict[str, Any]:
    """
    Store or update a user preference.
    """

    if not key or not key.strip():

        return {
            "success": False,
            "message": "Preference key is empty.",
        }

    success = save_preference(
        key=key.strip(),
        value=str(value),
        confidence=confidence,
    )

    return {
        "success": success,
        "key": key.strip(),
        "value": str(value),
    }


# ============================================================
# REMOVE PREFERENCE
# ============================================================

def remove_user_preference(
    key: str,
) -> dict[str, Any]:

    success = delete_preference(
        key
    )

    return {
        "success": success,
        "key": key,
    }


# ============================================================
# OBSERVE HABIT
# ============================================================

def observe(
    behavior: str,
    category: str | None = None,
    confidence: float = 0.5,
) -> dict[str, Any]:
    """
    Record an observed user behavior.

    This does NOT automatically mean it is a confirmed habit.
    """

    return observe_action(
        action=behavior,
        category=category,
        confidence=confidence,
    )


# ============================================================
# HABIT INSIGHTS
# ============================================================

def get_habit_insights() -> dict[str, Any]:

    habits = get_habits(
        limit=100
    )

    strong = get_high_confidence_habits(
        threshold=0.75
    )

    frequent = get_frequent_habits(
        minimum_occurrences=3
    )

    ranked = get_ranked_habits(
        limit=10
    )

    return {
        "total": len(habits),
        "strong": strong,
        "frequent": frequent,
        "ranked": ranked,
    }


# ============================================================
# PERSONAL CONTEXT
# ============================================================

def build_personal_context(
    max_memories: int = 20,
    max_preferences: int = 20,
    max_habits: int = 15,
) -> str:
    """
    Build a clean context block for the LLM.

    This function is intentionally defensive so an old or
    partially migrated database doesn't crash NOVA.
    """

    try:

        memories = get_all_memories(
            limit=max_memories
        )

        preferences = get_preferences()

        habits = get_ranked_habits(
            limit=max_habits
        )

    except Exception as error:

        print(
            f"[MEMORY WARNING] {error}"
        )

        return (
            "Personal memory is temporarily unavailable."
        )

    sections: list[str] = []

    # ========================================================
    # IDENTITY
    # ========================================================

    sections.append(
        "USER IDENTITY:\n"
        "- Name: Saksham\n"
        "- Name spelling: Saksham"
    )

    # ========================================================
    # MEMORIES
    # ========================================================

    if memories:

        memory_lines = [
            "KNOWN MEMORIES:"
        ]

        for item in memories:

            text = item.get(
                "memory"
            )

            if not text:
                continue

            category = item.get(
                "category",
                "general"
            )

            confidence = float(
                item.get(
                    "confidence",
                    1.0
                )
            )

            importance = float(
                item.get(
                    "importance",
                    0.5
                )
            )

            memory_lines.append(
                f"- {text} "
                f"[category={category}, "
                f"confidence={confidence:.2f}, "
                f"importance={importance:.2f}]"
            )

        if len(memory_lines) > 1:

            sections.append(
                "\n".join(memory_lines)
            )

    # ========================================================
    # PREFERENCES
    # ========================================================

    if preferences:

        preference_lines = [
            "KNOWN PREFERENCES:"
        ]

        for preference in preferences[
            :max_preferences
        ]:

            key = preference.get(
                "key"
            )

            value = preference.get(
                "value"
            )

            if key is None:
                continue

            preference_lines.append(
                f"- {key}: {value}"
            )

        if len(preference_lines) > 1:

            sections.append(
                "\n".join(preference_lines)
            )

    # ========================================================
    # HABITS
    # ========================================================

    if habits:

        habit_lines = [
            "OBSERVED BEHAVIORAL PATTERNS:"
        ]

        for habit in habits:

            name = habit.get(
                "habit"
            )

            if not name:
                continue

            category = habit.get(
                "category",
                "general"
            )

            confidence = float(
                habit.get(
                    "confidence",
                    0.0
                )
            )

            occurrences = int(
                habit.get(
                    "occurrences",
                    1
                )
            )

            strength = float(
                habit.get(
                    "strength",
                    0.0
                )
            )

            habit_lines.append(
                f"- {name} "
                f"[category={category}, "
                f"confidence={confidence:.2f}, "
                f"observations={occurrences}, "
                f"strength={strength:.2f}]"
            )

        if len(habit_lines) > 1:

            sections.append(
                "\n".join(habit_lines)
            )

    # ========================================================
    # SAFETY / INTERPRETATION
    # ========================================================

    sections.append(
        "MEMORY INTERPRETATION RULES:\n"
        "- Explicit memories are stronger than inferred habits.\n"
        "- Repeated behavior is evidence, not certainty.\n"
        "- Never invent personal information.\n"
        "- Use this context only when relevant.\n"
        "- If uncertain, say you are uncertain."
    )

    return "\n\n".join(
        sections
    )


# ============================================================
# SHORT CONTEXT
# ============================================================

def build_short_personal_context() -> str:
    """
    Smaller context for situations where the LLM
    needs to conserve context window.
    """

    try:

        memories = get_all_memories(
            limit=8
        )

        preferences = get_preferences()

        habits = get_ranked_habits(
            limit=5
        )

    except Exception:

        return (
            "User: Saksham."
        )

    lines = [
        "USER: Saksham"
    ]

    for memory in memories:

        text = memory.get(
            "memory"
        )

        if text:

            lines.append(
                f"Memory: {text}"
            )

    for preference in preferences[:8]:

        key = preference.get(
            "key"
        )

        value = preference.get(
            "value"
        )

        if key:

            lines.append(
                f"Preference: {key}={value}"
            )

    for habit in habits:

        name = habit.get(
            "habit"
        )

        if name:

            lines.append(
                f"Observed habit: {name}"
            )

    return "\n".join(
        lines
    )


# ============================================================
# CONSCIENCE STATUS
# ============================================================

def get_conscience_status() -> dict[str, Any]:
    """
    Diagnostic information about NOVA's personal context.
    """

    try:

        memories = get_all_memories(
            limit=1000
        )

        preferences = get_preferences()

        habits = get_habits(
            limit=1000
        )

        return {
            "success": True,
            "user": "Saksham",
            "memory_count": len(
                memories
            ),
            "preference_count": len(
                preferences
            ),
            "habit_count": len(
                habits
            ),
            "system": "NOVA Personal Context",
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error),
        }


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":

    print(
        "NOVA Conscience System"
    )

    print(
        get_conscience_status()
    )

    print(
        "\nPERSONAL CONTEXT\n"
    )

    print(
        build_personal_context()
    )
