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
                "SELECT thread_id, channel, intent, sentiment, escalated, response_ms, timestamp "
                "FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "thread_id": r[0], "channel": r[1], "intent": r[2],
                "sentiment": r[3], "escalated": bool(r[4]),
                "response_ms": r[5], "timestamp": r[6],
            }
            for r in rows
        ]

    def daily_trend(self, days: int = 14) -> List[Dict]:
        """Day-by-day breakdown of volume + escalations + avg sentiment."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self._conn() as c:
            rows = c.execute("""
                SELECT
                    substr(timestamp, 1, 10) AS day,
                    COUNT(*)                 AS total,
                    SUM(escalated)           AS escalated,
                    AVG(sentiment)           AS avg_sentiment,
                    AVG(response_ms)         AS avg_response_ms
                FROM events
                WHERE timestamp > ?
                GROUP BY day
                ORDER BY day ASC
            """, (since,)).fetchall()
        return [
            {
                "day": r[0],
                "total": r[1],
                "escalated": r[2] or 0,
                "avg_sentiment": round(r[3] or 0.0, 3),
                "avg_response_ms": round(r[4] or 0.0, 0),
            }
            for r in rows
        ]

    def response_time_histogram(self, days: int = 7) -> List[Dict]:
        """Bucketed response-time distribution (under 1s, 1-2s, 2-3s, 3-5s, 5s+)."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        buckets = [
            ("0-1s", 0, 1000),
            ("1-2s", 1000, 2000),
            ("2-3s", 2000, 3000),
            ("3-5s", 3000, 5000),
            ("5s+",  5000, 10**9),
        ]
        out = []
        with self._conn() as c:
            for label, lo, hi in buckets:
                count = c.execute(
                    "SELECT COUNT(*) FROM events WHERE timestamp > ? AND response_ms >= ? AND response_ms < ?",
                    (since, lo, hi),
                ).fetchone()[0]
                out.append({"bucket": label, "count": count})
        return out

    def percentiles(self, days: int = 7) -> Dict:
        """p50 / p95 response time computed in Python (SQLite has no PERCENTILE_CONT)."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self._conn() as c:
            rows = [r[0] for r in c.execute(
                "SELECT response_ms FROM events WHERE timestamp > ? ORDER BY response_ms ASC",
                (since,)
            ).fetchall() if r[0] is not None]
        if not rows:
            return {"p50": 0, "p95": 0, "p99": 0}
        def pct(p):
            idx = max(0, min(len(rows) - 1, int(round((p / 100.0) * (len(rows) - 1)))))
            return rows[idx]
        return {"p50": pct(50), "p95": pct(95), "p99": pct(99)}
