"""SQLite storage for saved reviews. All queries use bound parameters."""
import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    language TEXT NOT NULL,
    mode TEXT NOT NULL,
    code TEXT NOT NULL,
    error_text TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    finding_count INTEGER NOT NULL DEFAULT 0,
    result_json TEXT NOT NULL
)
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path):
    with connect(path) as conn:
        conn.execute(SCHEMA)


def save_review(path, language, mode, code, error_text, result):
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO reviews (created_at, language, mode, code, error_text, summary, finding_count, result_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), language, mode, code, error_text,
             result.get("summary", "")[:300], len(result.get("findings", [])), json.dumps(result)),
        )
        return cur.lastrowid


def list_reviews(path):
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT id, created_at, language, mode, summary, finding_count FROM reviews ORDER BY id DESC LIMIT 200"
        ).fetchall()
    return [dict(r) for r in rows]


def get_review(path, review_id):
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["result"] = json.loads(item.pop("result_json"))
    return item


def delete_review(path, review_id):
    with connect(path) as conn:
        return conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,)).rowcount > 0
