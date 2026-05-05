"""
Metrics collection for the analytics dashboard.
Tracks volume, intent distribution, sentiment, response time, and escalation rate.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List


class MetricsCollector:
    """Lightweight SQLite-backed metrics store with aggregation queries."""

    def __init__(self, db_path: str = "./data/metrics.db"):
        self.db_path = db_path
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
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT,
                    channel TEXT,
                    intent TEXT,
                    sentiment REAL,
                    escalated INTEGER,
                    response_ms INTEGER,
                    timestamp TEXT
                )
            """)

    def record(self, thread_id, channel, intent, sentiment, escalated=False, response_ms=0):
        with self._conn() as c:
            c.execute(
                "INSERT INTO events (thread_id, channel, intent, sentiment, escalated, response_ms, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (thread_id, channel, intent, sentiment, int(escalated),
                 response_ms, datetime.utcnow().isoformat()),
            )

    def summary(self, days: int = 7) -> Dict:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM events WHERE timestamp > ?", (since,)).fetchone()[0]
            escalated = c.execute(
                "SELECT COUNT(*) FROM events WHERE escalated = 1 AND timestamp > ?", (since,)
            ).fetchone()[0]
            avg_sentiment = c.execute(
                "SELECT AVG(sentiment) FROM events WHERE timestamp > ?", (since,)
            ).fetchone()[0] or 0.0
            avg_response = c.execute(
                "SELECT AVG(response_ms) FROM events WHERE timestamp > ?", (since,)
            ).fetchone()[0] or 0.0
            by_intent = dict(c.execute(
                "SELECT intent, COUNT(*) FROM events WHERE timestamp > ? GROUP BY intent", (since,)
            ).fetchall())
            by_channel = dict(c.execute(
                "SELECT channel, COUNT(*) FROM events WHERE timestamp > ? GROUP BY channel", (since,)
            ).fetchall())
        return {
            "total_messages": total,
            "escalation_rate": (escalated / total) if total else 0.0,
            "avg_sentiment": round(avg_sentiment, 2),
            "avg_response_ms": round(avg_response, 0),
            "by_intent": by_intent,
            "by_channel": by_channel,
        }

    def recent_events(self, limit: int = 50) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT thread_id, channel, intent, sentiment, escalated, timestamp "
                "FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "thread_id": r[0], "channel": r[1], "intent": r[2],
                "sentiment": r[3], "escalated": bool(r[4]), "timestamp": r[5],
            }
            for r in rows
        ]
