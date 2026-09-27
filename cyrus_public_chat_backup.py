import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "cyrus_users.db")


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_chat_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            memory TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_message(user_id, role, message):
    conn = get_db()

    conn.execute(
        """
        INSERT INTO user_messages
        (user_id, role, message, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            role,
            message,
            datetime.now(timezone.utc).isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_recent_messages(user_id, limit=14):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT role, message
        FROM user_messages
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit)
    ).fetchall()

    conn.close()

    rows = list(reversed(rows))

    return [
        {
            "role": row["role"],
            "message": row["message"]
        }
        for row in rows
    ]


def clear_chat(user_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM user_messages WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()


def add_memory(user_id, memory):
    memory = memory.strip()

    if not memory:
        return

    conn = get_db()

    existing = conn.execute(
        """
        SELECT id
        FROM user_memory
        WHERE user_id = ? AND memory = ?
        """,
        (user_id, memory)
    ).fetchone()

    if not existing:
        conn.execute(
            """
            INSERT INTO user_memory
            (user_id, memory, created_at)
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                memory,
                datetime.now(timezone.utc).isoformat()
            )
        )

    conn.commit()
    conn.close()


def get_memories(user_id, limit=20):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT memory
        FROM user_memory
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit)
    ).fetchall()

    conn.close()

    return [row["memory"] for row in rows]


def clear_memory(user_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM user_memory WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()


def forget_memory(user_id, keyword):
    keyword = keyword.strip().lower()

    if not keyword:
        return 0

    conn = get_db()

    cursor = conn.execute(
        """
        DELETE FROM user_memory
        WHERE user_id = ?
        AND LOWER(memory) LIKE ?
        """,
        (user_id, f"%{keyword}%")
    )

    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    return deleted


def build_user_context(user_id):
    memories = get_memories(user_id)
    messages = get_recent_messages(user_id)

    context = []

    if memories:
        context.append("USER MEMORY:")
        for memory in memories:
            context.append(f"- {memory}")

    if messages:
        context.append("\nRECENT CHAT:")
        for item in messages:
            context.append(
                f"{item['role'].upper()}: {item['message']}"
            )

    return "\n".join(context)