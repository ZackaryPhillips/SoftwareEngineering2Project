import os
import sqlite3
from pathlib import Path


class HistoryStore:
    def __init__(self, path: Path | None = None):
        if path is not None:
            self.path = path
        elif os.getenv("LOCALAPPDATA"):
            self.path = Path(os.environ["LOCALAPPDATA"]) / "SoftwareEngineering2Project" / "ai_history.sqlite3"
        else:
            self.path = Path.home() / ".softwareengineering2project" / "ai_history.sqlite3"

    def load(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []

        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                """
                SELECT id, description, ai_response, decision
                FROM ai_history
                ORDER BY created_at, id
                """
            ).fetchall()
        return [
            {
                "id": row[0],
                "description": row[1],
                "ai_response": row[2],
                "decision": row[3],
            }
            for row in rows
        ]

    def save(self, history_id: str, description: str, ai_response: str, decision: str):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_history (
                    id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    decision TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                )
                """
            )
            connection.execute(
                """
                INSERT INTO ai_history (id, description, ai_response, decision)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    description = excluded.description,
                    ai_response = excluded.ai_response,
                    decision = excluded.decision
                """,
                (history_id, description, ai_response, decision),
            )
