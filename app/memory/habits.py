
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.memory.memory import (
    record_habit,
    get_habits,
    delete_habit,
)


# ============================================================
# NOVA ADVANCED HABIT INTELLIGENCE
# ============================================================
#
# This module gives NOVA the ability to:
#
# - Observe repeated actions
# - Track frequency
# - Track confidence
# - Detect strong habits
# - Detect frequent habits
# - Generate habit insights
# - Categorize behaviors
# - Avoid treating a single action as a habit
# - Forget habits
# - Provide context to NOVA's conscience
#
# IMPORTANT:
# A habit is an OBSERVED PATTERN, not a guaranteed fact.
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_CONFIDENCE = 0.50

STRONG_HABIT_THRESHOLD = 0.75

VERY_STRONG_HABIT_THRESHOLD = 0.90

MIN_OBSERVATIONS_FOR_HABIT = 2

MIN_OBSERVATIONS_FOR_STRONG_HABIT = 3


# ============================================================
# CATEGORY DETECTION
# ============================================================

def infer_category(
    action: str,
) -> str:
    """
    Attempt to determine the category of an observed action.

    This is intentionally simple and deterministic.
    The LLM can later provide more sophisticated classification.
    """

    text = action.lower()

    categories = {

        "technology": [
            "code",
            "coding",
            "python",
            "javascript",
            "github",
            "terminal",
            "vscode",
            "programming",
            "developer",
            "website",
            "app",
            "software",
        ],

        "study": [
            "study",
            "studying",
            "exam",
            "homework",
            "assignment",
            "class",
            "school",
            "college",
            "lecture",
            "revision",
        ],

        "fitness": [
            "gym",
            "workout",
            "exercise",
            "running",
            "walking",
            "treadmill",
            "cycling",
            "training",
        ],

        "entertainment": [
            "youtube",
            "netflix",
            "movie",
            "music",
            "spotify",
            "gaming",
            "game",
        ],

        "communication": [
            "email",
            "message",
            "whatsapp",
            "telegram",
            "call",
            "meeting",
        ],

        "productivity": [
            "todo",
            "task",
            "calendar",
            "planning",
            "organize",
            "productivity",
        ],

        "browsing": [
            "safari",
            "chrome",
            "browser",
            "website",
            "search",
            "google",
        ],

    }

    for category, keywords in categories.items():

        if any(
            keyword in text
            for keyword in keywords
        ):

            return category

    return "general"


# ============================================================
# OBSERVE ACTION
# ============================================================

def observe_action(
    action: str,
    category: str | None = None,
    confidence: float = DEFAULT_CONFIDENCE,
) -> dict[str, Any]:
    """
    Record an observed user action.

    Repeated observations are handled by memory.record_habit().
    """

    if not action or not action.strip():

        return {
            "success": False,
            "message": "No action supplied.",
        }

    action = action.strip()

    if category is None:

        category = infer_category(
            action
        )

    success = record_habit(
        habit=action,
        category=category,
        confidence=confidence,
    )

    return {
        "success": success,
        "action": action,
        "category": category,
        "confidence": confidence,
        "observed_at": datetime.now().isoformat(),
    }


# ============================================================
# ALIAS
# ============================================================

def observe(
    behavior: str,
    category: str | None = None,
    confidence: float = DEFAULT_CONFIDENCE,
) -> dict[str, Any]:
    """
    Short alias for observe_action().
    """

    return observe_action(
        action=behavior,
        category=category,
        confidence=confidence,
    )


# ============================================================
# GET ALL KNOWN HABITS
# ============================================================

def get_known_habits(
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Return NOVA's currently known habits.
    """

    return get_habits(
        limit=limit
    )


# ============================================================
# HIGH CONFIDENCE HABITS
# ============================================================

def get_high_confidence_habits(
    threshold: float = STRONG_HABIT_THRESHOLD,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Return habits whose confidence exceeds the threshold.
    """

    habits = get_habits(
        limit=100
    )

    results = []

    for habit in habits:

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

        if (
            confidence >= threshold
            and occurrences >= MIN_OBSERVATIONS_FOR_HABIT
        ):

            results.append(
                habit
            )

    return results[:limit]


# ============================================================
# STRONG HABITS
# ============================================================

def get_strong_habits(
    threshold: float = STRONG_HABIT_THRESHOLD,
) -> list[dict[str, Any]]:

    return get_high_confidence_habits(
        threshold=threshold
    )


# ============================================================
# VERY STRONG HABITS
# ============================================================

def get_very_strong_habits(
    limit: int = 20,
) -> list[dict[str, Any]]:

    return get_high_confidence_habits(
        threshold=VERY_STRONG_HABIT_THRESHOLD,
        limit=limit,
    )


# ============================================================
# FREQUENT HABITS
# ============================================================

def get_frequent_habits(
    minimum_occurrences: int = 3,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Find behaviors that happen repeatedly.
    """

    habits = get_habits(
        limit=100
    )

    results = [

        habit

        for habit in habits

        if int(
            habit.get(
                "occurrences",
                0
            )
        ) >= minimum_occurrences

    ]

    results.sort(
        key=lambda item: int(
            item.get(
                "occurrences",
                0
            )
        ),
        reverse=True,
    )

    return results[:limit]


# ============================================================
# CATEGORY HABITS
# ============================================================

def get_habits_by_category(
    category: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Return habits belonging to a specific category.
    """

    if not category:
        return []

    habits = get_habits(
        limit=100
    )

    category = category.lower()

    results = [

        habit

        for habit in habits

        if str(
            habit.get(
                "category",
                "general"
            )
        ).lower() == category

    ]

    return results[:limit]


# ============================================================
# HABIT CONFIDENCE
# ============================================================

def get_habit_confidence(
    habit_name: str,
) -> float:
    """
    Return confidence for a particular habit.
    """

    habits = get_habits(
        limit=100
    )

    habit_name = habit_name.lower()

    for habit in habits:

        if str(
            habit.get(
                "habit",
                ""
            )
        ).lower() == habit_name:

            return float(
                habit.get(
                    "confidence",
                    0.0
                )
            )

    return 0.0


# ============================================================
# HABIT STRENGTH
# ============================================================

def calculate_habit_strength(
    habit: dict[str, Any],
) -> float:
    """
    Calculate a normalized habit strength score.

    This is separate from database confidence.
    """

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

    frequency_score = min(
        1.0,
        occurrences / 10.0
    )

    strength = (
        confidence * 0.7
        + frequency_score * 0.3
    )

    return round(
        min(
            1.0,
            strength
        ),
        3,
    )


# ============================================================
# RANK HABITS
# ============================================================

def get_ranked_habits(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Rank habits using confidence and frequency.
    """

    habits = get_habits(
        limit=100
    )

    ranked = []

    for habit in habits:

        item = dict(habit)

        item["strength"] = (
            calculate_habit_strength(
                habit
            )
        )

        ranked.append(
            item
        )

    ranked.sort(
        key=lambda item: item["strength"],
        reverse=True,
    )

    return ranked[:limit]


# ============================================================
# HABIT INSIGHTS
# ============================================================

def get_habit_insights() -> dict[str, Any]:
    """
    Generate structured information that conscience.py
    can give to the LLM.
    """

    habits = get_habits(
        limit=100
    )

    strong = get_high_confidence_habits()

    very_strong = get_very_strong_habits()

    frequent = get_frequent_habits()

    ranked = get_ranked_habits(
        limit=10
    )

    categories: dict[str, int] = {}

    for habit in habits:

        category = habit.get(
            "category",
            "general"
        )

        categories[category] = (
            categories.get(
                category,
                0
            )
            + 1
        )

    return {
        "total_habits": len(habits),

        "strong_habits": strong,

        "very_strong_habits": very_strong,

        "frequent_habits": frequent,

        "ranked_habits": ranked,

        "categories": categories,
    }


# ============================================================
# HABIT SUMMARY
# ============================================================

def habit_summary() -> dict[str, Any]:
    """
    Compact summary for NOVA.
    """

    insights = get_habit_insights()

    return {
        "total_habits": insights[
            "total_habits"
        ],

        "strong_habits": len(
            insights[
                "strong_habits"
            ]
        ),

        "very_strong_habits": len(
            insights[
                "very_strong_habits"
            ]
        ),

        "categories": insights[
            "categories"
        ],

        "top_habits": insights[
            "ranked_habits"
        ][:5],
    }


# ============================================================
# FORGET HABIT
# ============================================================

def forget_habit(
    habit_id: int,
) -> dict[str, Any]:
    """
    Delete a habit by database ID.
    """

    success = delete_habit(
        habit_id
    )

    return {
        "success": success,
        "habit_id": habit_id,
    }


# ============================================================
# FIND HABIT
# ============================================================

def find_habit(
    query: str,
) -> list[dict[str, Any]]:
    """
    Find habits matching a phrase.
    """

    if not query or not query.strip():
        return []

    query = query.lower()

    habits = get_habits(
        limit=100
    )

    return [

        habit

        for habit in habits

        if query in str(
            habit.get(
                "habit",
                ""
            )
        ).lower()

    ]


# ============================================================
# CONSCIENCE CONTEXT
# ============================================================

def build_habit_context(
    limit: int = 10,
) -> str:
    """
    Convert habit information into compact natural-language
    context for NOVA's LLM.
    """

    habits = get_ranked_habits(
        limit=limit
    )

    if not habits:

        return (
            "NOVA has not observed enough repeated "
            "behavior to identify reliable habits yet."
        )

    lines = [
        "OBSERVED USER HABITS:"
    ]

    for habit in habits:

        name = habit.get(
            "habit",
            "unknown"
        )

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

        lines.append(
            f"- {name} "
            f"[category={category}, "
            f"confidence={confidence:.2f}, "
            f"observations={occurrences}, "
            f"strength={strength:.2f}]"
        )

    lines.append(
        "\nIMPORTANT: These are observed patterns, "
        "not guaranteed facts."
    )

    return "\n".join(
        lines
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "NOVA Habit Intelligence"
    )

    print(
        habit_summary()
    )
