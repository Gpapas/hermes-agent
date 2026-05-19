from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from hermes_cli import kanban_db as kb


def test_connect_initialization_is_thread_safe(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    db_path = kb.kanban_db_path(board="default")
    kb._INITIALIZED_PATHS.discard(str(db_path.resolve()))

    errors: list[BaseException] = []
    barrier = threading.Barrier(8)

    def worker() -> None:
        try:
            barrier.wait(timeout=5)
            conn = kb.connect(board="default")
            conn.close()
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    with kb.connect(board="default") as conn:
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
    assert "max_retries" in cols


def test_connect_migrates_legacy_db_missing_session_id_before_index(tmp_path):
    db_path = tmp_path / "kanban.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE tasks (
                id                   TEXT PRIMARY KEY,
                title                TEXT NOT NULL,
                body                 TEXT,
                assignee             TEXT,
                status               TEXT NOT NULL,
                priority             INTEGER DEFAULT 0,
                created_by           TEXT,
                created_at           INTEGER NOT NULL,
                started_at           INTEGER,
                completed_at         INTEGER,
                workspace_kind       TEXT NOT NULL DEFAULT 'scratch',
                workspace_path       TEXT,
                branch_name          TEXT,
                claim_lock           TEXT,
                claim_expires        INTEGER,
                tenant               TEXT,
                result               TEXT,
                idempotency_key      TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                worker_pid           INTEGER,
                last_failure_error   TEXT,
                max_runtime_seconds  INTEGER,
                last_heartbeat_at    INTEGER,
                current_run_id       INTEGER,
                workflow_template_id TEXT,
                current_step_key     TEXT,
                skills               TEXT,
                model_override       TEXT,
                max_retries          INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO tasks (id, title, status, created_at)
            VALUES ('t_legacy', 'legacy task', 'ready', 1)
            """
        )
        conn.commit()
    finally:
        conn.close()

    kb._INITIALIZED_PATHS.discard(str(db_path.resolve()))

    with kb.connect(db_path) as migrated:
        cols = {row["name"] for row in migrated.execute("PRAGMA table_info(tasks)")}
        assert "session_id" in cols
        indexes = {
            row["name"]
            for row in migrated.execute("PRAGMA index_list(tasks)")
        }
        assert "idx_tasks_session_id" in indexes
        row = migrated.execute(
            "SELECT id, session_id FROM tasks WHERE id = 't_legacy'"
        ).fetchone()

    assert dict(row) == {"id": "t_legacy", "session_id": None}
