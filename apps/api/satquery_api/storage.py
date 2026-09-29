import json
import sqlite3
from pathlib import Path
from threading import Lock


class Store:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/satquery.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, payload TEXT NOT NULL, path TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def put_asset(self, asset_id: str, payload: dict, path: Path) -> None:
        with self.lock, self._connect() as connection:
            connection.execute("INSERT OR REPLACE INTO assets(id,payload,path) VALUES(?,?,?)", (asset_id, json.dumps(payload), str(path)))

    def get_asset(self, asset_id: str) -> tuple[dict, Path] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload,path FROM assets WHERE id=?", (asset_id,)).fetchone()
        return (json.loads(row["payload"]), Path(row["path"])) if row else None

    def list_assets(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM assets ORDER BY created_at DESC").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def delete_asset(self, asset_id: str) -> Path | None:
        record = self.get_asset(asset_id)
        if not record:
            return None
        with self.lock, self._connect() as connection:
            connection.execute("DELETE FROM assets WHERE id=?", (asset_id,))
        return record[1]

    def put_run(self, run_id: str, payload: dict, status: str = "complete") -> None:
        with self.lock, self._connect() as connection:
            connection.execute("INSERT OR REPLACE INTO runs(id,payload,status) VALUES(?,?,?)", (run_id, json.dumps(payload), status))

    def get_run(self, run_id: str) -> tuple[dict, str] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload,status FROM runs WHERE id=?", (run_id,)).fetchone()
        return (json.loads(row["payload"]), row["status"]) if row else None

    def list_runs(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload,status,created_at FROM runs ORDER BY created_at DESC").fetchall()
        return [{**json.loads(row["payload"]), "status": row["status"], "created_at": row["created_at"]} for row in rows]

    def set_run_status(self, run_id: str, status: str) -> bool:
        with self.lock, self._connect() as connection:
            cursor = connection.execute("UPDATE runs SET status=? WHERE id=?", (status, run_id))
        return cursor.rowcount > 0


STORE = Store()
