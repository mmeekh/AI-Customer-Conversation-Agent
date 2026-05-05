"""
Short-term conversation buffer (SQLite).
Used for the last N exchanges in active threads.
"""
import sqlite3
from datetime import datetime
from typing import List, Dict
from contextlib import contextmanager


class ShortTermMemory:
    """SQLite-backed rolling window of recent thread history."""

    def __init__(self, db_path: str = "./data/conversations.db", window_size: int = 10):
        self.db_path = db_path
        self.window_size = window_size
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    channel TEXT,
                    intent TEXT,
                    sentiment REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    msg_id TEXT PRIMARY KEY,
                    channel TEXT,
                    processed_at TEXT
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_thread ON history(thread_id)")

    def append(self, thread_id: str, role: str, content: str,
               channel: str = "gmail", intent: str = None, sentiment: float = None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO history (thread_id, role, content, channel, intent, sentiment, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (thread_id, role, content, channel, intent, sentiment,
                 datetime.utcnow().isoformat()),
            )

    def get_window(self, thread_id: str) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT role, content FROM history WHERE thread_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (thread_id, self.window_size),
            ).fetchall()
        return [{"role": r, "parts": [{"text": cnt}]} for r, cnt in reversed(rows)]

    def is_processed(self, msg_id: str) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM processed_messages WHERE msg_id = ?", (msg_id,)
            ).fetchone()
        return row is not None

    def mark_processed(self, msg_id: str, channel: str = "gmail"):
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO processed_messages VALUES (?, ?, ?)",
                (msg_id, channel, datetime.utcnow().isoformat()),
            )
