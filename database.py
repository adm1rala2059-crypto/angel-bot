import sqlite3

DB_PATH = "subscribers.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    for column, definition in [
        ("last_gift_index", "INTEGER DEFAULT -1"),
        ("last_accept_date", "TEXT"),
        ("streak", "INTEGER DEFAULT 0"),
        ("last_reengagement_date", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE subscribers ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def get_indices(chat_id: int) -> tuple[int, int]:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT last_phrase_index, last_gift_index FROM subscribers WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    conn.close()
    return row if row else (-1, -1)


def set_last_phrase_index(chat_id: int, index: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE subscribers SET last_phrase_index = ? WHERE chat_id = ?", (index, chat_id)
    )
    conn.commit()
    conn.close()


def set_last_gift_index(chat_id: int, index: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE subscribers SET last_gift_index = ? WHERE chat_id = ?", (index, chat_id)
    )
    conn.commit()
    conn.close()


def get_engagement(chat_id: int) -> tuple[str | None, int, str | None]:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT last_accept_date, streak, last_reengagement_date FROM subscribers WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    conn.close()
    return row if row else (None, 0, None)


def record_accept(chat_id: int, today: str, yesterday: str) -> int:
    last_accept_date, streak, _ = get_engagement(chat_id)
    if last_accept_date == today:
        new_streak = streak
    elif last_accept_date == yesterday:
        new_streak = streak + 1
    else:
        new_streak = 1

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE subscribers SET last_accept_date = ?, streak = ? WHERE chat_id = ?",
        (today, new_streak, chat_id),
    )
    conn.commit()
    conn.close()
    return new_streak


def set_last_reengagement_date(chat_id: int, date_str: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE subscribers SET last_reengagement_date = ? WHERE chat_id = ?",
        (date_str, chat_id),
    )
    conn.commit()
    conn.close()


def add_subscriber(chat_id: int, name: str = ""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO subscribers (chat_id, name) VALUES (?, ?)",
        (chat_id, name),
    )
    conn.commit()
    conn.close()


def remove_subscriber(chat_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


def get_all_subscribers():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT chat_id, name FROM subscribers").fetchall()
    conn.close()
    return rows


def count_subscribers() -> int:
    conn = sqlite3.connect(DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
    conn.close()
    return n
