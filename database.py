import sqlite3

DB_PATH = "subscribers.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id INTEGER PRIMARY KEY,
            name TEXT,
            last_phrase_index INTEGER DEFAULT -1
        )
        """
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
