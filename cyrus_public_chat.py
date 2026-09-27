import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "cyrus_users.db")


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now(timezone.utc).isoformat()


def init_chat_db():
    conn = get_db()

    # Existing memory table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            memory TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # New conversations table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Messages now belong to a conversation
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            conversation_id INTEGER,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # Add conversation_id to an old database if necessary
    columns = conn.execute(
        "PRAGMA table_info(user_messages)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    if "conversation_id" not in column_names:
        conn.execute(
            "ALTER TABLE user_messages ADD COLUMN conversation_id INTEGER"
        )

    conn.commit()
    conn.close()


def create_conversation(user_id, title="New Chat"):
    conn = get_db()

    timestamp = now()

    cursor = conn.execute(
        """
        INSERT INTO conversations
        (user_id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            title,
            timestamp,
            timestamp
        )
    )

    conversation_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return conversation_id


def get_conversations(user_id):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
        for row in rows
    ]


def conversation_belongs_to_user(user_id, conversation_id):
    conn = get_db()

    row = conn.execute(
        """
        SELECT id
        FROM conversations
        WHERE id = ? AND user_id = ?
        """,
        (
            conversation_id,
            user_id
        )
    ).fetchone()

    conn.close()

    return row is not None


def rename_conversation(user_id, conversation_id, title):
    title = title.strip()

    if not title:
        title = "New Chat"

    conn = get_db()

    conn.execute(
        """
        UPDATE conversations
        SET title = ?, updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            title[:100],
            now(),
            conversation_id,
            user_id
        )
    )

    conn.commit()
    conn.close()


def delete_conversation(user_id, conversation_id):
    conn = get_db()

    conn.execute(
        """
        DELETE FROM user_messages
        WHERE conversation_id = ?
        AND user_id = ?
        """,
        (
            conversation_id,
            user_id
        )
    )

    conn.execute(
        """
        DELETE FROM conversations
        WHERE id = ? AND user_id = ?
        """,
        (
            conversation_id,
            user_id
        )
    )

    conn.commit()
    conn.close()


def add_message(
    user_id,
    role,
    message,
    conversation_id=None
):
    conn = get_db()

    # Automatically create a conversation if needed
    if conversation_id is None:
        timestamp = now()

        cursor = conn.execute(
            """
            INSERT INTO conversations
            (user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                "New Chat",
                timestamp,
                timestamp
            )
        )

        conversation_id = cursor.lastrowid

    else:
        exists = conn.execute(
            """
            SELECT id
            FROM conversations
            WHERE id = ? AND user_id = ?
            """,
            (
                conversation_id,
                user_id
            )
        ).fetchone()

        if not exists:
            conn.close()
            return None

    conn.execute(
        """
        INSERT INTO user_messages
        (
            user_id,
            conversation_id,
            role,
            message,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            conversation_id,
            role,
            message,
            now()
        )
    )

    conn.execute(
        """
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            now(),
            conversation_id,
            user_id
        )
    )

    conn.commit()
    conn.close()

    return conversation_id


def get_recent_messages(
    user_id,
    conversation_id=None,
    limit=14
):
    conn = get_db()

    if conversation_id is None:
        rows = conn.execute(
            """
            SELECT role, message
            FROM user_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                user_id,
                limit
            )
        ).fetchall()

    else:
        rows = conn.execute(
            """
            SELECT role, message
            FROM user_messages
            WHERE user_id = ?
            AND conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                user_id,
                conversation_id,
                limit
            )
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


def clear_chat(user_id, conversation_id=None):
    conn = get_db()

    if conversation_id is None:
        conn.execute(
            """
            DELETE FROM user_messages
            WHERE user_id = ?
            """,
            (user_id,)
        )

    else:
        conn.execute(
            """
            DELETE FROM user_messages
            WHERE user_id = ?
            AND conversation_id = ?
            """,
            (
                user_id,
                conversation_id
            )
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
        (
            user_id,
            memory
        )
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
                now()
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
        (
            user_id,
            limit
        )
    ).fetchall()

    conn.close()

    return [
        row["memory"]
        for row in rows
    ]


def clear_memory(user_id):
    conn = get_db()

    conn.execute(
        """
        DELETE FROM user_memory
        WHERE user_id = ?
        """,
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
        (
            user_id,
            f"%{keyword}%"
        )
    )

    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    return deleted


def build_user_context(
    user_id,
    conversation_id=None
):
    memories = get_memories(user_id)

    messages = get_recent_messages(
        user_id,
        conversation_id,
        limit=14
    )

    context = []

    if memories:
        context.append("USER MEMORY:")

        for memory in memories:
            context.append(
                f"- {memory}"
            )

    if messages:
        context.append("\nCURRENT CONVERSATION:")

        for item in messages:
            context.append(
                f"{item['role'].upper()}: {item['message']}"
            )

    return "\n".join(context)