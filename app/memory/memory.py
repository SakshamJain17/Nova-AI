from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# ============================================================
# NOVA MEMORY DATABASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "nova_memory.db"


# ============================================================
# CONNECTION
# ============================================================

def get_connection() -> sqlite3.Connection:
    """
    Create a connection to NOVA's SQLite database.
    """

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# DATABASE HELPERS
# ============================================================

def _table_exists(
    conn: sqlite3.Connection,
    table_name: str,
) -> bool:

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def _column_exists(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:

    if not _table_exists(
        conn,
        table_name,
    ):
        return

    if not _column_exists(
        conn,
        table_name,
        column_name,
    ):

        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database() -> None:
    """
    Create NOVA's database and safely migrate
    older database versions.
    """

    conn = get_connection()

    try:

        # ====================================================
        # MEMORIES
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                memory TEXT NOT NULL,

                category TEXT DEFAULT 'general',

                importance REAL DEFAULT 0.5,

                confidence REAL DEFAULT 1.0,

                source TEXT DEFAULT 'user',

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ====================================================
        # PREFERENCES
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS preferences (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                key TEXT UNIQUE NOT NULL,

                value TEXT,

                confidence REAL DEFAULT 1.0,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ====================================================
        # HABITS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS habits (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                habit TEXT NOT NULL,

                category TEXT DEFAULT 'general',

                confidence REAL DEFAULT 0.5,

                occurrences INTEGER DEFAULT 1,

                first_seen TEXT DEFAULT CURRENT_TIMESTAMP,

                last_seen TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ====================================================
        # CONVERSATIONS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                role TEXT NOT NULL,

                content TEXT NOT NULL,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ====================================================
        # MIGRATE OLD MEMORIES TABLE
        # ====================================================

        _ensure_column(
            conn,
            "memories",
            "category",
            "TEXT DEFAULT 'general'",
        )

        _ensure_column(
            conn,
            "memories",
            "importance",
            "REAL DEFAULT 0.5",
        )

        _ensure_column(
            conn,
            "memories",
            "confidence",
            "REAL DEFAULT 1.0",
        )

        _ensure_column(
            conn,
            "memories",
            "source",
            "TEXT DEFAULT 'user'",
        )

        _ensure_column(
            conn,
            "memories",
            "created_at",
            "TEXT",
        )

        _ensure_column(
            conn,
            "memories",
            "updated_at",
            "TEXT",
        )

        # ====================================================
        # MIGRATE OLD HABITS TABLE
        # ====================================================

        _ensure_column(
            conn,
            "habits",
            "category",
            "TEXT DEFAULT 'general'",
        )

        _ensure_column(
            conn,
            "habits",
            "confidence",
            "REAL DEFAULT 0.5",
        )

        _ensure_column(
            conn,
            "habits",
            "occurrences",
            "INTEGER DEFAULT 1",
        )

        _ensure_column(
            conn,
            "habits",
            "first_seen",
            "TEXT",
        )

        _ensure_column(
            conn,
            "habits",
            "last_seen",
            "TEXT",
        )

        # ====================================================
        # FIX NULL VALUES FROM OLD DATABASES
        # ====================================================

        conn.execute(
            """
            UPDATE memories
            SET confidence = 1.0
            WHERE confidence IS NULL
            """
        )

        conn.execute(
            """
            UPDATE memories
            SET importance = 0.5
            WHERE importance IS NULL
            """
        )

        conn.execute(
            """
            UPDATE memories
            SET category = 'general'
            WHERE category IS NULL
            """
        )

        conn.execute(
            """
            UPDATE habits
            SET confidence = 0.5
            WHERE confidence IS NULL
            """
        )

        conn.execute(
            """
            UPDATE habits
            SET occurrences = 1
            WHERE occurrences IS NULL
            """
        )

        # ====================================================
        # COMMIT
        # ====================================================

        conn.commit()

    finally:

        conn.close()


# ============================================================
# MEMORY
# ============================================================

def save_memory(
    memory: str,
    category: str = "general",
    importance: float = 0.7,
    confidence: float = 1.0,
    source: str = "user",
) -> bool:

    if not memory or not memory.strip():

        return False

    initialize_database()

    now = datetime.now().isoformat()

    conn = get_connection()

    try:

        conn.execute(
            """
            INSERT INTO memories
            (
                memory,
                category,
                importance,
                confidence,
                source,
                created_at,
                updated_at
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory.strip(),
                category,
                importance,
                confidence,
                source,
                now,
                now,
            ),
        )

        conn.commit()

        return True

    finally:

        conn.close()


# ============================================================
# GET ALL MEMORIES
# ============================================================

def get_all_memories(
    limit: int = 100,
) -> list[dict[str, Any]]:

    initialize_database()

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT

                id,
                memory,
                category,
                importance,
                confidence,
                source,
                created_at,
                updated_at

            FROM memories

            ORDER BY
                importance DESC,
                updated_at DESC

            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# SEARCH MEMORIES
# ============================================================

def search_memories(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:

    initialize_database()

    if not query or not query.strip():

        return []

    conn = get_connection()

    try:

        pattern = f"%{query.strip()}%"

        rows = conn.execute(
            """
            SELECT

                id,
                memory,
                category,
                importance,
                confidence,
                source,
                created_at,
                updated_at

            FROM memories

            WHERE
                memory LIKE ?
                OR category LIKE ?

            ORDER BY
                importance DESC,
                updated_at DESC

            LIMIT ?
            """,
            (
                pattern,
                pattern,
                limit,
            ),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# DELETE MEMORY BY ID
# ============================================================

def delete_memory(
    memory_id: int,
) -> bool:

    initialize_database()

    conn = get_connection()

    try:

        cursor = conn.execute(
            """
            DELETE FROM memories
            WHERE id = ?
            """,
            (memory_id,),
        )

        conn.commit()

        return cursor.rowcount > 0

    finally:

        conn.close()


# ============================================================
# FORGET MEMORY
# ============================================================

def forget_memory(
    text: str,
) -> int:

    initialize_database()

    if not text or not text.strip():

        return 0

    conn = get_connection()

    try:

        cursor = conn.execute(
            """
            DELETE FROM memories
            WHERE memory LIKE ?
            """,
            (f"%{text.strip()}%",),
        )

        deleted = cursor.rowcount

        conn.commit()

        return deleted

    finally:

        conn.close()


# ============================================================
# PREFERENCES
# ============================================================

def save_preference(
    key: str,
    value: str,
    confidence: float = 1.0,
) -> bool:

    initialize_database()

    if not key or not key.strip():

        return False

    conn = get_connection()

    try:

        now = datetime.now().isoformat()

        conn.execute(
            """
            INSERT INTO preferences
            (
                key,
                value,
                confidence,
                created_at,
                updated_at
            )

            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(key)

            DO UPDATE SET

                value = excluded.value,

                confidence = excluded.confidence,

                updated_at = excluded.updated_at
            """,
            (
                key.strip(),
                value,
                confidence,
                now,
                now,
            ),
        )

        conn.commit()

        return True

    finally:

        conn.close()


# ============================================================
# GET PREFERENCES
# ============================================================

def get_preferences() -> list[dict[str, Any]]:

    initialize_database()

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT

                id,
                key,
                value,
                confidence,
                created_at,
                updated_at

            FROM preferences

            ORDER BY updated_at DESC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# GET ONE PREFERENCE
# ============================================================

def get_preference(
    key: str,
) -> Optional[str]:

    initialize_database()

    conn = get_connection()

    try:

        row = conn.execute(
            """
            SELECT value
            FROM preferences
            WHERE key = ?
            """,
            (key,),
        ).fetchone()

        if row is None:

            return None

        return row["value"]

    finally:

        conn.close()


# ============================================================
# DELETE PREFERENCE
# ============================================================

def delete_preference(
    key: str,
) -> bool:

    initialize_database()

    conn = get_connection()

    try:

        cursor = conn.execute(
            """
            DELETE FROM preferences
            WHERE key = ?
            """,
            (key,),
        )

        conn.commit()

        return cursor.rowcount > 0

    finally:

        conn.close()


# ============================================================
# HABITS
# ============================================================

def record_habit(
    habit: str,
    category: str = "general",
    confidence: float = 0.5,
) -> bool:

    initialize_database()

    if not habit or not habit.strip():

        return False

    habit = habit.strip()

    conn = get_connection()

    try:

        now = datetime.now().isoformat()

        existing = conn.execute(
            """
            SELECT

                id,
                occurrences,
                confidence

            FROM habits

            WHERE habit = ?
            """,
            (habit,),
        ).fetchone()

        if existing:

            occurrences = (
                existing["occurrences"] or 0
            ) + 1

            old_confidence = (
                existing["confidence"]
                or 0.5
            )

            # Repeated observations gradually
            # increase confidence.

            new_confidence = min(
                0.99,
                max(
                    old_confidence,
                    confidence,
                )
                + 0.03,
            )

            conn.execute(
                """
                UPDATE habits

                SET

                    occurrences = ?,

                    confidence = ?,

                    last_seen = ?

                WHERE id = ?
                """,
                (
                    occurrences,
                    new_confidence,
                    now,
                    existing["id"],
                ),
            )

        else:

            conn.execute(
                """
                INSERT INTO habits
                (
                    habit,
                    category,
                    confidence,
                    occurrences,
                    first_seen,
                    last_seen
                )

                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    habit,
                    category,
                    confidence,
                    1,
                    now,
                    now,
                ),
            )

        conn.commit()

        return True

    finally:

        conn.close()


# ============================================================
# GET HABITS
# ============================================================

def get_habits(
    limit: int = 50,
) -> list[dict[str, Any]]:

    initialize_database()

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT

                id,
                habit,
                category,
                confidence,
                occurrences,
                first_seen,
                last_seen

            FROM habits

            ORDER BY

                confidence DESC,

                occurrences DESC,

                last_seen DESC

            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# DELETE HABIT
# ============================================================

def delete_habit(
    habit_id: int,
) -> bool:

    initialize_database()

    conn = get_connection()

    try:

        cursor = conn.execute(
            """
            DELETE FROM habits
            WHERE id = ?
            """,
            (habit_id,),
        )

        conn.commit()

        return cursor.rowcount > 0

    finally:

        conn.close()


# ============================================================
# CONVERSATION MEMORY
# ============================================================

def save_conversation(
    role: str,
    content: str,
) -> bool:

    initialize_database()

    if not content or not content.strip():

        return False

    conn = get_connection()

    try:

        conn.execute(
            """
            INSERT INTO conversations
            (
                role,
                content
            )

            VALUES (?, ?)
            """,
            (
                role,
                content.strip(),
            ),
        )

        conn.commit()

        return True

    finally:

        conn.close()


# ============================================================
# RECENT CONVERSATION
# ============================================================

def get_recent_conversation(
    limit: int = 20,
) -> list[dict[str, Any]]:

    initialize_database()

    conn = get_connection()

    try:

        rows = conn.execute(
            """
            SELECT

                role,
                content,
                created_at

            FROM conversations

            ORDER BY id DESC

            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        results = [
            dict(row)
            for row in rows
        ]

        results.reverse()

        return results

    finally:

        conn.close()


# ============================================================
# CLEAR CONVERSATION
# ============================================================

def clear_conversation() -> None:

    initialize_database()

    conn = get_connection()

    try:

        conn.execute(
            "DELETE FROM conversations"
        )

        conn.commit()

    finally:

        conn.close()


# ============================================================
# MEMORY STATISTICS
# ============================================================

def get_memory_summary() -> dict[str, Any]:

    initialize_database()

    conn = get_connection()

    try:

        memories = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM memories
            """
        ).fetchone()["count"]

        preferences = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM preferences
            """
        ).fetchone()["count"]

        habits = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM habits
            """
        ).fetchone()["count"]

        conversations = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM conversations
            """
        ).fetchone()["count"]

        return {
            "memories": memories,
            "preferences": preferences,
            "habits": habits,
            "conversations": conversations,
            "database": str(DB_PATH),
        }

    finally:

        conn.close()


# ============================================================
# DATABASE HEALTH
# ============================================================

def get_database_status() -> dict[str, Any]:

    try:

        initialize_database()

        conn = get_connection()

        try:

            tables = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name
                """
            ).fetchall()

            return {
                "success": True,
                "database": str(DB_PATH),
                "tables": [
                    row["name"]
                    for row in tables
                ],
                "summary": get_memory_summary(),
            }

        finally:

            conn.close()

    except Exception as error:

        return {
            "success": False,
            "database": str(DB_PATH),
            "error": str(error),
        }


# ============================================================
# AUTO INITIALIZATION
# ============================================================

if __name__ == "__main__":

    initialize_database()

    print(
        "NOVA memory database initialized."
    )

    print(
        get_database_status()
    )
