import os
from datetime import datetime

import libsql

_conn = None


def get_connection():
    global _conn
    if _conn is None:
        _conn = libsql.connect(
            database=os.environ["TURSO_DATABASE_URL"],
            auth_token=os.environ["TURSO_AUTH_TOKEN"],
        )
    return _conn


def run(sql: str, params: tuple = (), commit: bool = False):
    """Executes a query, retrying once on a fresh connection if the cached one is dead.

    Turso's remote (Hrana) connection can go stale after several hours idle in this
    long-running process ("stream not found" ValueError) — the cached global connection
    doesn't detect that on its own, so on any failure we drop it and reconnect once.
    """
    global _conn
    conn = get_connection()
    try:
        result = conn.execute(sql, params)
        if commit:
            conn.commit()
        return result
    except Exception:
        _conn = None
        conn = get_connection()
        result = conn.execute(sql, params)
        if commit:
            conn.commit()
        return result


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id INTEGER PRIMARY KEY,
            name TEXT,
            last_phrase_index INTEGER DEFAULT -1,
            last_gift_index INTEGER DEFAULT -1,
            last_accept_date TEXT,
            streak INTEGER DEFAULT 0,
            last_reengagement_date TEXT
        )
        """
    )

    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(subscribers)").fetchall()}
    for column, definition in [
        ("last_gift_index", "INTEGER DEFAULT -1"),
        ("last_accept_date", "TEXT"),
        ("streak", "INTEGER DEFAULT 0"),
        ("last_reengagement_date", "TEXT"),
        ("subscribed_at", "TEXT"),
        ("preferred_category", "TEXT"),
    ]:
        if column not in existing_columns:
            conn.execute(f"ALTER TABLE subscribers ADD COLUMN {column} {definition}")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER,
            message_type TEXT,
            text TEXT,
            sent_at TEXT,
            accepted_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS unsubscribe_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            name TEXT,
            reason TEXT,
            unsubscribed_at TEXT
        )
        """
    )
    conn.commit()


def get_meta(key: str) -> str | None:
    row = run("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(key: str, value: str):
    run(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
        commit=True,
    )


def log_event(chat_id: int, message_id: int, message_type: str, text: str, sent_at: str):
    run(
        "INSERT INTO events (chat_id, message_id, message_type, text, sent_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, message_id, message_type, text, sent_at),
        commit=True,
    )


def mark_event_accepted(chat_id: int, message_id: int, accepted_at: str):
    run(
        "UPDATE events SET accepted_at = ? WHERE chat_id = ? AND message_id = ?",
        (accepted_at, chat_id, message_id),
        commit=True,
    )


def get_event_text(chat_id: int, message_id: int) -> str | None:
    row = run(
        "SELECT text FROM events WHERE chat_id = ? AND message_id = ?",
        (chat_id, message_id),
    ).fetchone()
    return row[0] if row else None


def get_events_since(since_iso: str) -> list[tuple]:
    return run(
        """
        SELECT e.chat_id, s.name, e.sent_at, e.message_type, e.text, e.accepted_at
        FROM events e
        LEFT JOIN subscribers s ON s.chat_id = e.chat_id
        WHERE e.sent_at >= ?
        ORDER BY e.sent_at
        """,
        (since_iso,),
    ).fetchall()


def get_indices(chat_id: int) -> tuple[int, int]:
    row = run(
        "SELECT last_phrase_index, last_gift_index FROM subscribers WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    return row if row else (-1, -1)


def set_last_phrase_index(chat_id: int, index: int):
    run("UPDATE subscribers SET last_phrase_index = ? WHERE chat_id = ?", (index, chat_id), commit=True)


def set_preferred_category(chat_id: int, category: str | None):
    run(
        "UPDATE subscribers SET preferred_category = ? WHERE chat_id = ?",
        (category, chat_id),
        commit=True,
    )


def get_preferred_category(chat_id: int) -> str | None:
    row = run(
        "SELECT preferred_category FROM subscribers WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return row[0] if row else None


def get_engagement(chat_id: int) -> tuple[str | None, int, str | None]:
    row = run(
        "SELECT last_accept_date, streak, last_reengagement_date FROM subscribers WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    return row if row else (None, 0, None)


def record_accept(chat_id: int, today: str, yesterday: str) -> int:
    last_accept_date, streak, _ = get_engagement(chat_id)
    if last_accept_date == today:
        new_streak = streak
    elif last_accept_date == yesterday:
        new_streak = streak + 1
    else:
        new_streak = 1

    run(
        "UPDATE subscribers SET last_accept_date = ?, streak = ? WHERE chat_id = ?",
        (today, new_streak, chat_id),
        commit=True,
    )
    return new_streak


def set_last_reengagement_date(chat_id: int, date_str: str):
    run(
        "UPDATE subscribers SET last_reengagement_date = ? WHERE chat_id = ?",
        (date_str, chat_id),
        commit=True,
    )


def add_subscriber(chat_id: int, name: str = "") -> bool:
    """Adds a subscriber if not already present. Returns True if this was a new subscription."""
    already_exists = run(
        "SELECT 1 FROM subscribers WHERE chat_id = ?", (chat_id,)
    ).fetchone() is not None
    run(
        "INSERT OR IGNORE INTO subscribers (chat_id, name, subscribed_at) VALUES (?, ?, ?)",
        (chat_id, name, datetime.now().isoformat()),
        commit=True,
    )
    return not already_exists


def remove_subscriber(chat_id: int, reason: str = "unknown"):
    row = run("SELECT name FROM subscribers WHERE chat_id = ?", (chat_id,)).fetchone()
    name = row[0] if row else None
    run(
        "INSERT INTO unsubscribe_log (chat_id, name, reason, unsubscribed_at) VALUES (?, ?, ?, ?)",
        (chat_id, name, reason, datetime.now().isoformat()),
        commit=True,
    )
    run("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,), commit=True)


def get_unsubscribe_log() -> list[tuple]:
    return run(
        "SELECT chat_id, name, reason, unsubscribed_at FROM unsubscribe_log ORDER BY unsubscribed_at"
    ).fetchall()


def get_all_subscribers():
    return run("SELECT chat_id, name FROM subscribers").fetchall()


def count_subscribers() -> int:
    return run("SELECT COUNT(*) FROM subscribers").fetchone()[0]
